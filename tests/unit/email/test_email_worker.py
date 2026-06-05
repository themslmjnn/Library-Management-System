# tests/unit/email/test_email_worker.py

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import structlog.testing
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.email_worker import (
    BATCH_SIZE,
    POLL_INTERVAL_SECONDS,
    _process_batch,
    run_email_worker,
)
from src.email.enums import EmailSendingStatus, EmailType
from src.email.repository import PendingEmailRepository
from tests.factories import make_member


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pending_record(
    email_id: int = 1,
    retry_count: int = 0,
    recipient: str = "user@example.com",
    subject: str = "Test Subject",
    html_body: str = "<p>hello</p>",
    text_body: str = "hello",
    email_type: EmailType = EmailType.invite,
    recipient_user_id: int = 1,
) -> MagicMock:
    record = MagicMock()
    record.id = email_id
    record.retry_count = retry_count
    record.recipient = recipient
    record.subject = subject
    record.html_body = html_body
    record.text_body = text_body
    record.email_type = email_type
    record.recipient_user_id = recipient_user_id
    return record


# ===========================================================================
# TestProcessBatch
# ===========================================================================


class TestProcessBatch:
    async def test_calls_send_with_correct_arguments(self, mocker):
        record = _make_pending_record(
            recipient="user@example.com",
            subject="Hello",
            html_body="<p>hi</p>",
            text_body="hi",
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mock_send = mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_send.assert_awaited_once_with(
            subject=record.subject,
            to_email=record.recipient,
            html_body=record.html_body,
            text_body=record.text_body,
        )

    async def test_calls_mark_sent_after_successful_send(self, mocker):
        record = _make_pending_record()

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mock_mark_sent = mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_mark_sent.assert_awaited_once()
        assert mock_mark_sent.call_args.args[1] is record

    async def test_does_not_call_mark_failed_after_successful_send(self, mocker):
        record = _make_pending_record()

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        mock_mark_failed = mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_mark_failed.assert_not_awaited()

    async def test_calls_mark_failed_after_send_failure(self, mocker):
        record = _make_pending_record()
        error_message = "connection refused"

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=Exception(error_message),
        )

        mock_mark_failed = mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_mark_failed.assert_awaited_once()
        call_args = mock_mark_failed.call_args
        assert call_args.args[1] is record
        assert error_message in call_args.args[2]

    async def test_does_not_call_mark_sent_after_send_failure(self, mocker):
        record = _make_pending_record()

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=Exception("failed"),
        )

        mock_mark_sent = mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_mark_sent.assert_not_awaited()

    async def test_processes_multiple_records_in_batch(self, mocker):
        records = [_make_pending_record(email_id=i) for i in range(3)]

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=records,
        )

        mock_send = mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        await _process_batch()

        assert mock_send.await_count == 3

    async def test_continues_processing_after_one_failure(self, mocker):
        """
        One failed send must not stop the remaining records
        from being processed.
        """
        records = [
            _make_pending_record(email_id=1),
            _make_pending_record(email_id=2),
            _make_pending_record(email_id=3),
        ]

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=records,
        )

        # First call fails, rest succeed
        mock_send = mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=[Exception("fail"), None, None],
        )

        mock_mark_sent = mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            new_callable=AsyncMock,
        )

        await _process_batch()

        # All 3 attempted, 2 succeeded
        assert mock_send.await_count == 3
        assert mock_mark_sent.await_count == 2

    async def test_does_nothing_when_no_pending_records(self, mocker):
        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[],
        )

        mock_send = mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        await _process_batch()

        mock_send.assert_not_awaited()

    async def test_logs_processing_start(self, mocker):
        records = [_make_pending_record()]

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=records,
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            await _process_batch()

        assert any(log["event"] == "email_worker_processing" for log in logs)

    async def test_logs_pending_email_sent_on_success(self, mocker):
        record = _make_pending_record(email_id=42)

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_sent",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            await _process_batch()

        sent_logs = [l for l in logs if l["event"] == "pending_email_sent"]
        assert len(sent_logs) == 1
        assert sent_logs[0]["email_id"] == 42

    async def test_logs_attempt_failed_on_failure(self, mocker):
        record = _make_pending_record(email_id=7)

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=Exception("timeout"),
        )

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            await _process_batch()

        failed_logs = [l for l in logs if l["event"] == "pending_email_attempt_failed"]
        assert len(failed_logs) == 1
        assert failed_logs[0]["email_id"] == 7

    async def test_logs_exhausted_retries_when_retry_count_reaches_3(self, mocker):
        # After mark_failed_attempt is called, the record's retry_count
        # needs to reflect 3 for the exhausted log to fire.
        # We simulate this by having mark_failed_attempt set retry_count=3 on the record.
        record = _make_pending_record(email_id=5, retry_count=2)

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=Exception("error"),
        )

        async def mock_mark_failed(db, rec, error):
            rec.retry_count = 3  # simulate repository incrementing the count

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            side_effect=mock_mark_failed,
        )

        with structlog.testing.capture_logs() as logs:
            await _process_batch()

        exhausted_logs = [
            l for l in logs if l["event"] == "pending_email_exhausted_retries"
        ]
        assert len(exhausted_logs) == 1
        assert exhausted_logs[0]["email_id"] == 5

    async def test_does_not_log_exhausted_when_retry_count_below_3(self, mocker):
        record = _make_pending_record(email_id=5, retry_count=0)

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.get_pending",
            new_callable=AsyncMock,
            return_value=[record],
        )

        mocker.patch(
            "src.core.email_worker._send",
            new_callable=AsyncMock,
            side_effect=Exception("error"),
        )

        async def mock_mark_failed(db, rec, error):
            rec.retry_count = 1  # only incremented once, below threshold

        mocker.patch(
            "src.core.email_worker.PendingEmailRepository.mark_failed_attempt",
            side_effect=mock_mark_failed,
        )

        with structlog.testing.capture_logs() as logs:
            await _process_batch()

        exhausted_logs = [
            l for l in logs if l["event"] == "pending_email_exhausted_retries"
        ]
        assert len(exhausted_logs) == 0


# ===========================================================================
# TestRunEmailWorker
# ===========================================================================


class TestRunEmailWorker:
    async def test_logs_worker_started(self, mocker):
        mocker.patch(
            "src.core.email_worker._process_batch",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError,
        )

        with structlog.testing.capture_logs() as logs:
            with pytest.raises(asyncio.CancelledError):
                await run_email_worker()

        assert any(log["event"] == "email_worker_started" for log in logs)

    async def test_reraises_cancelled_error(self, mocker):
        mocker.patch(
            "src.core.email_worker._process_batch",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError,
        )

        with pytest.raises(asyncio.CancelledError):
            await run_email_worker()

    async def test_logs_stopping_on_cancellation(self, mocker):
        mocker.patch(
            "src.core.email_worker._process_batch",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError,
        )

        with structlog.testing.capture_logs() as logs:
            with pytest.raises(asyncio.CancelledError):
                await run_email_worker()

        assert any(log["event"] == "email_worker_stopping" for log in logs)

    async def test_does_not_crash_on_unexpected_exception(self, mocker):
        """
        An unexpected error in _process_batch must be logged and swallowed.
        The worker continues running. We verify by having it raise once,
        then raise CancelledError to stop the loop cleanly.
        """
        mocker.patch(
            "src.core.email_worker._process_batch",
            new_callable=AsyncMock,
            side_effect=[Exception("db outage"), asyncio.CancelledError],
        )

        mocker.patch(
            "src.core.email_worker.asyncio.sleep",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            with pytest.raises(asyncio.CancelledError):
                await run_email_worker()

        assert any(log["event"] == "email_worker_unexpected_error" for log in logs)

    async def test_logs_unexpected_error_details(self, mocker):
        mocker.patch(
            "src.core.email_worker._process_batch",
            new_callable=AsyncMock,
            side_effect=[Exception("specific error message"), asyncio.CancelledError],
        )

        mocker.patch(
            "src.core.email_worker.asyncio.sleep",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            with pytest.raises(asyncio.CancelledError):
                await run_email_worker()

        error_logs = [l for l in logs if l["event"] == "email_worker_unexpected_error"]
        assert len(error_logs) >= 1
        assert "specific error message" in error_logs[0]["error"]

    async def test_calls_process_batch_on_each_cycle(self, mocker):
        call_count = 0

        async def mock_batch():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise asyncio.CancelledError

        mocker.patch(
            "src.core.email_worker._process_batch",
            side_effect=mock_batch,
        )

        mocker.patch(
            "src.core.email_worker.asyncio.sleep",
            new_callable=AsyncMock,
        )

        with pytest.raises(asyncio.CancelledError):
            await run_email_worker()

        assert call_count == 3
