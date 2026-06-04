# 7. tests/unit/email/test_email_activation.py
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import structlog.testing

from src.core.config import settings
from tests.constants import (
    FAKE_ACTIVATION_CODE,
    FAKE_EMAIL,
    FAKE_INVITE_TOKEN,
    RESEND_URL,
)
from utils.email import (
    _activation_code_html,
    _activation_code_text,
    _invite_email_html,
    _invite_email_text,
    _send,
    send_account_activation_code,
    send_invite_email,
)


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


class TestSendInviteEmail:
    async def test_delegates_to_send_with_correct_email(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_invite_email(FAKE_EMAIL, FAKE_INVITE_TOKEN)

        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs

        assert call_kwargs["to_email"] == FAKE_EMAIL

    async def test_delegates_correct_subject(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_invite_email(FAKE_EMAIL, FAKE_INVITE_TOKEN)

        subject = mock_send.call_args.kwargs["subject"]

        assert subject
        assert len(subject) > 5

    async def test_passes_raw_token_not_hash(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_invite_email(FAKE_EMAIL, FAKE_INVITE_TOKEN)

        kwargs = mock_send.call_args.kwargs

        assert FAKE_INVITE_TOKEN in kwargs["html_body"]
        assert FAKE_INVITE_TOKEN in kwargs["text_body"]

    @pytest.mark.asyncio
    async def test_token_not_empty_string(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_invite_email(FAKE_EMAIL, "")

        mock_send.assert_awaited_once()


class TestInviteEmailHtml:
    def test_activation_link_contains_raw_token(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert FAKE_INVITE_TOKEN in html

    def test_activation_link_contains_app_url(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert settings.APP_URL in html

    def test_activation_link_has_token_query_param(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert f"token={FAKE_INVITE_TOKEN}" in html

    def test_expiry_hours_mentioned_in_body(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert str(settings.INVITE_TOKEN_EXPIRES_HOURS) in html

    def test_is_valid_html_string(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert html.strip().startswith("<!DOCTYPE html>") or "<html" in html
        assert "</html>" in html

    def test_different_tokens_produce_different_links(self):
        html_a = _invite_email_html("token_aaa")
        html_b = _invite_email_html("token_bbb")

        assert html_a != html_b

    def test_token_appears_in_href(self):
        html = _invite_email_html(FAKE_INVITE_TOKEN)

        assert 'href="' in html
        assert f"token={FAKE_INVITE_TOKEN}" in html


class TestInviteEmailText:
    def test_activation_link_contains_raw_token(self):
        text = _invite_email_text(FAKE_INVITE_TOKEN)

        assert FAKE_INVITE_TOKEN in text

    def test_activation_link_contains_app_url(self):
        text = _invite_email_text(FAKE_INVITE_TOKEN)

        assert settings.APP_URL in text

    def test_activation_link_has_token_query_param(self):
        text = _invite_email_text(FAKE_INVITE_TOKEN)

        assert f"token={FAKE_INVITE_TOKEN}" in text

    def test_expiry_hours_mentioned_in_body(self):
        text = _invite_email_text(FAKE_INVITE_TOKEN)

        assert str(settings.INVITE_TOKEN_EXPIRES_HOURS) in text

    def test_is_plain_text_no_html_tags(self):
        text = _invite_email_text(FAKE_INVITE_TOKEN)

        assert "<" not in text
        assert ">" not in text

    def test_different_tokens_produce_different_links(self):
        text_a = _invite_email_text("token_aaa")
        text_b = _invite_email_text("token_bbb")

        assert text_a != text_b

    def test_html_and_text_share_same_activation_link(self):
        token = "consistent_token_xyz"
        expected_link = f"{settings.APP_URL}/activate_with_token?token={token}"

        html = _invite_email_html(token)
        text = _invite_email_text(token)

        assert expected_link in html
        assert expected_link in text


class TestSendAccountActivationCode:
    async def test_delegates_to_send_with_correct_email(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_code(FAKE_EMAIL, FAKE_ACTIVATION_CODE)

        mock_send.assert_awaited_once()
        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_delegates_correct_subject(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_code(FAKE_EMAIL, FAKE_ACTIVATION_CODE)

        subject = mock_send.call_args.kwargs["subject"]

        assert subject
        assert len(subject) > 5

    async def test_passes_raw_code_in_both_bodies(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_code(FAKE_EMAIL, FAKE_ACTIVATION_CODE)

        kwargs = mock_send.call_args.kwargs

        assert FAKE_ACTIVATION_CODE in kwargs["html_body"]
        assert FAKE_ACTIVATION_CODE in kwargs["text_body"]

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_code(FAKE_EMAIL, FAKE_ACTIVATION_CODE)

        assert mock_send.await_count == 1


class TestActivationCodeHtml:
    def test_code_appears_in_body(self):
        html = _activation_code_html(FAKE_ACTIVATION_CODE)

        assert FAKE_ACTIVATION_CODE in html

    def test_expiry_minutes_mentioned(self):
        html = _activation_code_html(FAKE_ACTIVATION_CODE)

        assert str(settings.ACTIVATION_CODE_EXPIRES_MINUTES) in html

    def test_is_valid_html_string(self):
        html = _activation_code_html(FAKE_ACTIVATION_CODE)

        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "</html>" in html

    def test_sender_name_in_footer(self):
        html = _activation_code_html(FAKE_ACTIVATION_CODE)

        assert settings.MAIL_FROM_NAME in html

    def test_different_codes_produce_different_output(self):
        html_a = _activation_code_html("111111")
        html_b = _activation_code_html("999999")

        assert html_a != html_b

    def test_no_activation_link(self):
        html = _activation_code_html(FAKE_ACTIVATION_CODE)

        assert "?token=" not in html


class TestActivationCodeText:
    def test_code_appears_in_body(self):
        text = _activation_code_text(FAKE_ACTIVATION_CODE)

        assert FAKE_ACTIVATION_CODE in text

    def test_expiry_minutes_mentioned(self):
        text = _activation_code_text(FAKE_ACTIVATION_CODE)

        assert str(settings.ACTIVATION_CODE_EXPIRES_MINUTES) in text

    def test_is_plain_text_no_html_tags(self):
        text = _activation_code_text(FAKE_ACTIVATION_CODE)

        assert "<" not in text
        assert ">" not in text

    def test_different_codes_produce_different_output(self):
        text_a = _activation_code_text("111111")
        text_b = _activation_code_text("999999")

        assert text_a != text_b

    def test_no_activation_link(self):
        text = _activation_code_text(FAKE_ACTIVATION_CODE)

        assert "?token=" not in text

    def test_html_and_text_carry_identical_code(self):
        code = "563847"
        html = _activation_code_html(code)
        text = _activation_code_text(code)

        assert code in html
        assert code in text
