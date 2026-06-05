# tests/unit/email/test_pending_email_repository.py

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailSendingStatus, EmailType
from src.email.models import PendingEmail
from src.email.repository import PendingEmailRepository
from tests.factories import make_member, make_library_admin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _insert_pending_email(
    test_db: AsyncSession,
    *,
    recipient: str = "user@example.com",
    subject: str = "Test",
    html_body: str = "<p>hi</p>",
    text_body: str = "hi",
    email_type: EmailType = EmailType.invite,
    status: EmailSendingStatus = EmailSendingStatus.pending,
    retry_count: int = 0,
    last_error: str | None = None,
    triggered_by: int | None = None,
    recipient_user_id: int | None = None,
) -> PendingEmail:
    """
    Inserts a PendingEmail record directly bypassing the repository's
    create() method so we can set status freely for test setup.
    """
    record = PendingEmail(
        recipient=recipient,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        email_type=email_type,
        status=status,
        retry_count=retry_count,
        last_error=last_error,
        triggered_by=triggered_by,
        recipient_user_id=recipient_user_id,
    )
    test_db.add(record)
    await test_db.commit()
    await test_db.refresh(record)
    return record


# ===========================================================================
# TestCreate
# ===========================================================================


class TestCreate:
    async def test_record_added_to_session_without_commit(self, test_db: AsyncSession):
        """
        create() must call db.add() but NOT commit.
        The caller owns the transaction boundary.
        After create(), before commit, the record exists in the session
        but not yet in the database from another session's perspective.
        We verify the record is in the session's identity map.
        """
        record = PendingEmailRepository.create(
            test_db,
            recipient="user@example.com",
            subject="Subject",
            html_body="<p>html</p>",
            text_body="text",
            email_type=EmailType.invite,
        )

        # Record is in the session (pending flush/commit)
        assert record in test_db.new

    async def test_all_fields_stored_correctly(self, test_db: AsyncSession):
        user = await make_member(test_db)
        admin = await make_library_admin(test_db)

        record = PendingEmailRepository.create(
            test_db,
            recipient="target@example.com",
            subject="My Subject",
            html_body="<p>html body</p>",
            text_body="text body",
            email_type=EmailType.activation_with_code,
            triggered_by=admin.id,
            recipient_user_id=user.id,
        )

        await test_db.commit()
        await test_db.refresh(record)

        assert record.recipient == "target@example.com"
        assert record.subject == "My Subject"
        assert record.html_body == "<p>html body</p>"
        assert record.text_body == "text body"
        assert record.email_type == EmailType.activation_with_code
        assert record.triggered_by == admin.id
        assert record.recipient_user_id == user.id

    async def test_default_status_is_pending(self, test_db: AsyncSession):
        record = PendingEmailRepository.create(
            test_db,
            recipient="user@example.com",
            subject="Subject",
            html_body="<p>x</p>",
            text_body="x",
            email_type=EmailType.invite,
        )

        await test_db.commit()
        await test_db.refresh(record)

        assert record.status == EmailSendingStatus.pending

    async def test_default_retry_count_is_zero(self, test_db: AsyncSession):
        record = PendingEmailRepository.create(
            test_db,
            recipient="user@example.com",
            subject="Subject",
            html_body="<p>x</p>",
            text_body="x",
            email_type=EmailType.invite,
        )

        await test_db.commit()
        await test_db.refresh(record)

        assert record.retry_count == 0

    async def test_triggered_by_defaults_to_none(self, test_db: AsyncSession):
        record = PendingEmailRepository.create(
            test_db,
            recipient="user@example.com",
            subject="Subject",
            html_body="<p>x</p>",
            text_body="x",
            email_type=EmailType.activation_with_code,
        )

        await test_db.commit()
        await test_db.refresh(record)

        assert record.triggered_by is None


# ===========================================================================
# TestGetPending
# ===========================================================================


class TestGetPending:
    async def test_returns_only_pending_status_records(self, test_db: AsyncSession):
        pending = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending
        )
        await _insert_pending_email(test_db, status=EmailSendingStatus.sent)
        await _insert_pending_email(test_db, status=EmailSendingStatus.failed)

        results = await PendingEmailRepository.get_pending(test_db)

        result_ids = [r.id for r in results]
        assert pending.id in result_ids
        assert all(r.status == EmailSendingStatus.pending for r in results)

    async def test_does_not_return_sent_records(self, test_db: AsyncSession):
        await _insert_pending_email(test_db, status=EmailSendingStatus.sent)

        results = await PendingEmailRepository.get_pending(test_db)

        assert all(r.status != EmailSendingStatus.sent for r in results)

    async def test_does_not_return_failed_records(self, test_db: AsyncSession):
        await _insert_pending_email(test_db, status=EmailSendingStatus.failed)

        results = await PendingEmailRepository.get_pending(test_db)

        assert all(r.status != EmailSendingStatus.failed for r in results)

    async def test_does_not_return_records_with_retry_count_3_or_more(
        self, test_db: AsyncSession
    ):
        """
        Records stuck at retry_count >= 3 are considered exhausted.
        The worker should not keep attempting them.
        """
        exhausted = await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.pending,
            retry_count=3,
        )
        fresh = await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.pending,
            retry_count=0,
            recipient="fresh@example.com",
        )

        results = await PendingEmailRepository.get_pending(test_db)

        result_ids = [r.id for r in results]
        assert exhausted.id not in result_ids
        assert fresh.id in result_ids

    async def test_ordered_oldest_first(self, test_db: AsyncSession):
        """
        Oldest records processed first — nothing starves.
        """
        first = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, recipient="first@example.com"
        )
        second = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, recipient="second@example.com"
        )
        third = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, recipient="third@example.com"
        )

        results = await PendingEmailRepository.get_pending(test_db)

        result_ids = [r.id for r in results]
        assert result_ids.index(first.id) < result_ids.index(second.id)
        assert result_ids.index(second.id) < result_ids.index(third.id)

    async def test_respects_limit_parameter(self, test_db: AsyncSession):
        for i in range(5):
            await _insert_pending_email(
                test_db,
                status=EmailSendingStatus.pending,
                recipient=f"user{i}@example.com",
            )

        results = await PendingEmailRepository.get_pending(test_db, limit=2)

        assert len(results) == 2

    async def test_returns_empty_list_when_no_pending(self, test_db: AsyncSession):
        await _insert_pending_email(test_db, status=EmailSendingStatus.sent)

        results = await PendingEmailRepository.get_pending(test_db)

        assert results == []


# ===========================================================================
# TestGetAllFailed
# ===========================================================================


class TestGetAllFailed:
    async def test_returns_only_failed_records(self, test_db: AsyncSession):
        failed = await _insert_pending_email(test_db, status=EmailSendingStatus.failed)
        await _insert_pending_email(test_db, status=EmailSendingStatus.pending)
        await _insert_pending_email(test_db, status=EmailSendingStatus.sent)

        results, total = await PendingEmailRepository.get_all_failed(test_db)

        result_ids = [r.id for r in results]
        assert failed.id in result_ids
        assert all(r.status == EmailSendingStatus.failed for r in results)

    async def test_does_not_return_pending_or_sent(self, test_db: AsyncSession):
        await _insert_pending_email(test_db, status=EmailSendingStatus.pending)
        await _insert_pending_email(test_db, status=EmailSendingStatus.sent)

        results, total = await PendingEmailRepository.get_all_failed(test_db)

        assert results == []
        assert total == 0

    async def test_returns_correct_total_count(self, test_db: AsyncSession):
        for i in range(4):
            await _insert_pending_email(
                test_db,
                status=EmailSendingStatus.failed,
                recipient=f"failed{i}@example.com",
            )

        _, total = await PendingEmailRepository.get_all_failed(test_db)

        assert total == 4

    async def test_respects_skip_and_limit(self, test_db: AsyncSession):
        for i in range(5):
            await _insert_pending_email(
                test_db,
                status=EmailSendingStatus.failed,
                recipient=f"failed{i}@example.com",
            )

        results, total = await PendingEmailRepository.get_all_failed(
            test_db, skip=2, limit=2
        )

        assert len(results) == 2
        assert total == 5


# ===========================================================================
# TestGetFailedByTriggeredBy
# ===========================================================================


class TestGetFailedByTriggeredBy:
    async def test_returns_only_records_for_given_triggered_by(
        self, test_db: AsyncSession
    ):
        admin1 = await make_library_admin(test_db)
        admin2 = await make_library_admin(test_db)

        admin1_email = await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.failed,
            triggered_by=admin1.id,
        )
        await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.failed,
            triggered_by=admin2.id,
            recipient="other@example.com",
        )

        results, total = await PendingEmailRepository.get_failed_by_triggered_by(
            test_db, triggered_by=admin1.id
        )

        result_ids = [r.id for r in results]
        assert admin1_email.id in result_ids
        assert total == 1

    async def test_does_not_return_other_users_emails(self, test_db: AsyncSession):
        admin1 = await make_library_admin(test_db)
        admin2 = await make_library_admin(test_db)

        await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.failed,
            triggered_by=admin2.id,
        )

        results, total = await PendingEmailRepository.get_failed_by_triggered_by(
            test_db, triggered_by=admin1.id
        )

        assert results == []
        assert total == 0

    async def test_returns_correct_total(self, test_db: AsyncSession):
        admin = await make_library_admin(test_db)

        for i in range(3):
            await _insert_pending_email(
                test_db,
                status=EmailSendingStatus.failed,
                triggered_by=admin.id,
                recipient=f"user{i}@example.com",
            )

        _, total = await PendingEmailRepository.get_failed_by_triggered_by(
            test_db, triggered_by=admin.id
        )

        assert total == 3

    async def test_respects_skip_and_limit(self, test_db: AsyncSession):
        admin = await make_library_admin(test_db)

        for i in range(5):
            await _insert_pending_email(
                test_db,
                status=EmailSendingStatus.failed,
                triggered_by=admin.id,
                recipient=f"user{i}@example.com",
            )

        results, total = await PendingEmailRepository.get_failed_by_triggered_by(
            test_db, triggered_by=admin.id, skip=1, limit=2
        )

        assert len(results) == 2
        assert total == 5


# ===========================================================================
# TestGetById
# ===========================================================================


class TestGetById:
    async def test_returns_correct_record(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db)

        result = await PendingEmailRepository.get_by_id(test_db, record.id)

        assert result is not None
        assert result.id == record.id
        assert result.recipient == record.recipient

    async def test_returns_none_for_unknown_id(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db)
        non_existent_id = record.id + 999999

        result = await PendingEmailRepository.get_by_id(test_db, non_existent_id)

        assert result is None


# ===========================================================================
# TestMarkSent
# ===========================================================================


class TestMarkSent:
    async def test_sets_status_to_sent(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db, status=EmailSendingStatus.pending)

        await PendingEmailRepository.mark_sent(test_db, record)

        await test_db.refresh(record)

        assert record.status == EmailSendingStatus.sent

    async def test_sets_sent_at_to_current_time(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db, status=EmailSendingStatus.pending)

        before = datetime.now(timezone.utc)
        await PendingEmailRepository.mark_sent(test_db, record)
        after = datetime.now(timezone.utc)

        await test_db.refresh(record)

        assert record.sent_at is not None
        assert before <= record.sent_at <= after

    async def test_change_persisted_after_commit(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db, status=EmailSendingStatus.pending)

        await PendingEmailRepository.mark_sent(test_db, record)

        # Expire and re-fetch from DB to confirm persistence
        test_db.expire(record)
        await test_db.refresh(record)

        assert record.status == EmailSendingStatus.sent


# ===========================================================================
# TestMarkFailedAttempt
# ===========================================================================


class TestMarkFailedAttempt:
    async def test_increments_retry_count(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, retry_count=1
        )

        await PendingEmailRepository.mark_failed_attempt(test_db, record, "some error")

        await test_db.refresh(record)

        assert record.retry_count == 2

    async def test_stores_last_error(self, test_db: AsyncSession):
        record = await _insert_pending_email(test_db, status=EmailSendingStatus.pending)
        error_message = "connection refused"

        await PendingEmailRepository.mark_failed_attempt(test_db, record, error_message)

        await test_db.refresh(record)

        assert record.last_error == error_message

    async def test_sets_status_to_failed_at_retry_count_3(self, test_db: AsyncSession):
        # retry_count starts at 2, mark_failed_attempt increments to 3
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, retry_count=2
        )

        await PendingEmailRepository.mark_failed_attempt(test_db, record, "error")

        await test_db.refresh(record)

        assert record.retry_count == 3
        assert record.status == EmailSendingStatus.failed

    async def test_does_not_set_status_to_failed_below_retry_count_3(
        self, test_db: AsyncSession
    ):
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, retry_count=0
        )

        await PendingEmailRepository.mark_failed_attempt(test_db, record, "error")

        await test_db.refresh(record)

        assert record.retry_count == 1
        assert record.status == EmailSendingStatus.pending

    async def test_change_persisted_after_commit(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.pending, retry_count=0
        )

        await PendingEmailRepository.mark_failed_attempt(
            test_db, record, "network error"
        )

        test_db.expire(record)
        await test_db.refresh(record)

        assert record.retry_count == 1
        assert record.last_error == "network error"


# ===========================================================================
# TestResetForRetry
# ===========================================================================


class TestResetForRetry:
    async def test_sets_status_back_to_pending(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.failed, retry_count=3
        )

        await PendingEmailRepository.reset_for_retry(test_db, record)

        await test_db.refresh(record)

        assert record.status == EmailSendingStatus.pending

    async def test_resets_retry_count_to_zero(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db, status=EmailSendingStatus.failed, retry_count=3
        )

        await PendingEmailRepository.reset_for_retry(test_db, record)

        await test_db.refresh(record)

        assert record.retry_count == 0

    async def test_clears_last_error(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.failed,
            retry_count=3,
            last_error="previous error",
        )

        await PendingEmailRepository.reset_for_retry(test_db, record)

        await test_db.refresh(record)

        assert record.last_error is None

    async def test_change_persisted_after_commit(self, test_db: AsyncSession):
        record = await _insert_pending_email(
            test_db,
            status=EmailSendingStatus.failed,
            retry_count=3,
            last_error="old error",
        )

        await PendingEmailRepository.reset_for_retry(test_db, record)

        test_db.expire(record)
        await test_db.refresh(record)

        assert record.status == EmailSendingStatus.pending
        assert record.retry_count == 0
        assert record.last_error is None
