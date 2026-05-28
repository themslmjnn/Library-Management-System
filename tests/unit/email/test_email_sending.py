
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest
import pytest_asyncio
import structlog.testing

from src.core.config import settings
from src.utils.email import (
    _invite_email_html,
    _invite_email_text,
    _send,
    send_invite_email,
)
 
FAKE_TOKEN = "raw_invite_token_abc123"
FAKE_EMAIL = "invited_user@example.com"
RESEND_URL = "https://api.resend.com/emails"
 
 
def _make_mock_response(status_code: int = 200) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = status_code
 
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.text = f'{{"error": "resend error {status_code}"}}'
    else:
        mock_response.raise_for_status.return_value = None
 
    return mock_response
 
 
def _patch_async_client(mock_response: MagicMock):
    mock_post = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.post = mock_post
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    return mock_client_instance, mock_post

class TestSendTransport:
    async def test_posts_to_resend_url(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, mock_post = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        await _send(
            subject="Test Subject",
            to_email=FAKE_EMAIL,
            html_body="<p>hello</p>",
            text_body="hello",
        )
 
        mock_post.assert_awaited_once()
        call_args = mock_post.call_args

        assert call_args[0][0] == RESEND_URL
 
    async def test_payload_structure(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, mock_post = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        subject = "Payload Test"
        html = "<p>html body</p>"
        text = "text body"
 
        await _send(
            subject=subject,
            to_email=FAKE_EMAIL,
            html_body=html,
            text_body=text,
        )
 
        payload = mock_post.call_args.kwargs["json"]
 
        assert payload["to"] == [FAKE_EMAIL]
        assert payload["subject"] == subject
        assert payload["html"] == html
        assert payload["text"] == text
        assert settings.MAIL_FROM in payload["from"]
        assert settings.MAIL_FROM_NAME in payload["from"]
 
    async def test_authorization_header(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, mock_post = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        await _send(
            subject="Header Test",
            to_email=FAKE_EMAIL,
            html_body="<p>x</p>",
            text_body="x",
        )
 
        headers = mock_post.call_args.kwargs["headers"]

        assert headers["Authorization"] == f"Bearer {settings.RESEND_API_KEY}"
        assert headers["Content-Type"] == "application/json"
 
    async def test_timeout_is_set(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, mock_post = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        await _send(
            subject="Timeout Test",
            to_email=FAKE_EMAIL,
            html_body="<p>x</p>",
            text_body="x",
        )
 
        timeout = mock_post.call_args.kwargs.get("timeout")

        assert timeout == pytest.approx(10.0), f"Expected timeout=10.0, got {timeout}"
        assert timeout > 0
 
    async def test_raise_for_status_is_called_on_success(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, _ = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        await _send(
            subject="Status Check",
            to_email=FAKE_EMAIL,
            html_body="<p>x</p>",
            text_body="x",
        )
 
        mock_response.raise_for_status.assert_called_once()

class TestSendLogging:
    async def test_logs_email_sent_on_success(self, mocker):
        mock_response = _make_mock_response(200)
        mock_client, _ = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        with structlog.testing.capture_logs() as logs:
            await _send(
                subject="Log Test",
                to_email=FAKE_EMAIL,
                html_body="<p>x</p>",
                text_body="x",
            )

        sent_log = next(log for log in logs if log["event"] == "email_sent")
 
        assert any(log["event"] == "email_sent" for log in logs)
        assert sent_log["to_email"] == FAKE_EMAIL
        assert sent_log["subject"] == "Log Test"
 
    async def test_logs_email_send_failed_on_http_error(self, mocker):
        mock_response = _make_mock_response(422)
        mock_client, _ = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        with structlog.testing.capture_logs() as logs:
            await _send(
                subject="Error Test",
                to_email=FAKE_EMAIL,
                html_body="<p>x</p>",
                text_body="x",
            )
 
        failed_log = next(log for log in logs if log["event"] == "email_send_failed")

        assert any(log["event"] == "email_send_failed" for log in logs)
        assert failed_log["status_code"] == 422
        assert failed_log["to_email"] == FAKE_EMAIL
 
    async def test_logs_email_send_failed_on_generic_exception(self, mocker):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            side_effect=Exception("connection refused")
        )

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client_instance,
        )
 
        with structlog.testing.capture_logs() as logs:
            await _send(
                subject="Generic Error Test",
                to_email=FAKE_EMAIL,
                html_body="<p>x</p>",
                text_body="x",
            )
 
        failed_log = next(log for log in logs if log["event"] == "email_send_failed")

        assert any(log["event"] == "email_send_failed" for log in logs)
        assert "connection refused" in failed_log["error"]
        assert failed_log["error_type"] == "Exception"

class TestSendExceptionSwallowing: 
    async def test_swallows_http_status_error(self, mocker):
        mock_response = _make_mock_response(500)
        mock_client, _ = _patch_async_client(mock_response)

        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client,
        )
 
        await _send("s", FAKE_EMAIL, "<p>x</p>", "x")
 
    async def test_swallows_connection_error(self, mocker):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            side_effect=httpx.ConnectError("unreachable")
        )
        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client_instance,
        )
 
        await _send("s", FAKE_EMAIL, "<p>x</p>", "x")
 
    async def test_swallows_timeout_error(self, mocker):
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )
        
        mocker.patch(
            "src.utils.email.httpx.AsyncClient", 
            return_value=mock_client_instance,
        )
 
        await _send("s", FAKE_EMAIL, "<p>x</p>", "x")