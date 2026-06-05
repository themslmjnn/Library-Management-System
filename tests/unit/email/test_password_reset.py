# 8. tests/unit/email/test_password_reset.py
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import structlog.testing

from src.auth.schemas import CreateResetPasswordRequest, ResetPasswordRequest
from src.auth.service import AuthService
from src.core.config import settings
from src.users.repository import UserRepositoryBase
from tests.conftest import make_member
from tests.constants import (
    CORRECT_PASSWORD,
    FAKE_EMAIL,
    FAKE_RESET_TOKEN,
    NEW_PASSWORD,
)
from tests.factories import make_user_with_reset_token
from utils.custom_exceptions import (
    ExpiredResetPasswordTokenError,
    InvalidCredentialsError,
    InvalidResetPasswordTokenError,
)
from utils.email import (
    _reset_password_html,
    _reset_password_text,
    send_reset_password_token,
)


class TestResetPasswordHtml:
    def test_token_appears_in_body(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in html

    def test_reset_link_contains_app_url(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert settings.APP_URL in html

    def test_reset_link_has_token_query_param(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert f"token={FAKE_RESET_TOKEN}" in html

    def test_reset_link_points_to_reset_page_not_request_endpoint(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)
        expected = f"{settings.APP_URL}/reset_password?token={FAKE_RESET_TOKEN}"

        assert expected in html

    def test_expiry_minutes_mentioned(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in html

    def test_is_valid_html_string(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "</html>" in html

    def test_token_appears_in_href(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert 'href="' in html
        assert f"token={FAKE_RESET_TOKEN}" in html

    def test_different_tokens_produce_different_links(self):
        html_a = _reset_password_html("token_aaa")
        html_b = _reset_password_html("token_bbb")

        assert html_a != html_b


class TestResetPasswordText:
    def test_token_appears_in_body(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in text

    def test_reset_link_contains_app_url(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert settings.APP_URL in text

    def test_reset_link_has_token_query_param(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert f"token={FAKE_RESET_TOKEN}" in text

    def test_reset_link_points_to_reset_page_not_request_endpoint(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)
        expected = f"{settings.APP_URL}/reset_password?token={FAKE_RESET_TOKEN}"

        assert expected in text

    def test_expiry_minutes_mentioned(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in text

    def test_is_plain_text_no_html_tags(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert "<" not in text
        assert ">" not in text

    def test_different_tokens_produce_different_links(self):
        text_a = _reset_password_text("token_aaa")
        text_b = _reset_password_text("token_bbb")

        assert text_a != text_b

    def test_html_and_text_share_identical_reset_link(self):
        token = "consistent_token_xyz"
        expected_link = f"{settings.APP_URL}/reset_password?token={token}"

        assert expected_link in _reset_password_html(token)
        assert expected_link in _reset_password_text(token)


class TestSendResetPasswordToken:
    async def test_delegates_to_send_with_correct_email(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )
        await send_reset_password_token(FAKE_EMAIL, FAKE_RESET_TOKEN)

        mock_send.assert_awaited_once()
        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_delegates_correct_subject(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )
        await send_reset_password_token(FAKE_EMAIL, FAKE_RESET_TOKEN)

        subject = mock_send.call_args.kwargs["subject"]
        assert subject
        assert len(subject) > 5

    async def test_passes_raw_token_in_both_bodies(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )
        await send_reset_password_token(FAKE_EMAIL, FAKE_RESET_TOKEN)

        kwargs = mock_send.call_args.kwargs

        assert FAKE_RESET_TOKEN in kwargs["html_body"]
        assert FAKE_RESET_TOKEN in kwargs["text_body"]

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )
        await send_reset_password_token(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert mock_send.await_count == 1


class TestCreateResetPasswordRequestService:
    async def test_stores_token_hash_for_known_user(self, test_db):
        user = await make_member(test_db, password=CORRECT_PASSWORD)

        with patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        ):
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier=user.email),
            )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.reset_password_token_hash is not None

    async def test_stores_expiry_for_known_user(self, test_db):
        user = await make_member(test_db, password=CORRECT_PASSWORD)

        with patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        ):
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier=user.email),
            )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.reset_password_token_expires_at is not None
        assert user_with_session.session.reset_password_token_expires_at > datetime.now(
            timezone.utc
        )

    async def test_fires_email_task_for_known_user(self, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mock_email = mocker.patch(
            "src.auth.service.send_reset_password_token",
            new_callable=AsyncMock,
        )

        await AuthService.create_reset_password_request(
            test_db,
            CreateResetPasswordRequest(identifier=user.email),
        )

        await asyncio.sleep(0)

        mock_email.assert_awaited_once()
        assert mock_email.call_args.args[0] == user.email

    async def test_does_not_raise_for_unknown_identifier(self, test_db):
        with patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        ):
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier="nobody@example.com"),
            )

    async def test_does_not_fire_email_for_unknown_identifier(self, test_db, mocker):
        mock_email = mocker.patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        )

        await AuthService.create_reset_password_request(
            test_db,
            CreateResetPasswordRequest(identifier="nobody@example.com"),
        )

        mock_email.assert_not_awaited()

    async def test_accepts_username_as_identifier(self, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        )

        await AuthService.create_reset_password_request(
            test_db,
            CreateResetPasswordRequest(identifier=user.username),
        )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.reset_password_token_hash is not None

    async def test_accepts_phone_number_as_identifier(self, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        )

        await AuthService.create_reset_password_request(
            test_db,
            CreateResetPasswordRequest(identifier=user.phone_number),
        )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.reset_password_token_hash is not None

    async def test_logs_info_on_success(self, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        )

        with structlog.testing.capture_logs() as logs:
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier=user.email),
            )

        assert any(log["event"] == "reset_password_request_created" for log in logs)

    async def test_logs_info_not_warning_for_unknown_user(self, test_db):
        with structlog.testing.capture_logs() as logs:
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier="nobody@example.com"),
            )

        failed_logs = [
            log
            for log in logs
            if log["event"] == "reset_password_request_creation_failed"
        ]

        assert failed_logs, "Expected a log event for unknown identifier"
        assert all(log["log_level"] == "info" for log in failed_logs)


class TestResetPasswordService:
    async def test_valid_token_updates_password_hash(self, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
        old_hash = user.password_hash

        await AuthService.reset_password(
            test_db,
            ResetPasswordRequest(
                identifier=user.email,
                reset_token=raw_token,
                new_password=NEW_PASSWORD,
            ),
        )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.password_hash != old_hash

    async def test_valid_token_clears_reset_token_fields(self, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)

        await AuthService.reset_password(
            test_db,
            ResetPasswordRequest(
                identifier=user.email,
                reset_token=raw_token,
                new_password=NEW_PASSWORD,
            ),
        )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.reset_password_token_hash is None
        assert user_with_session.session.reset_password_token_expires_at is None

    async def test_valid_token_invalidates_existing_sessions(self, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        old_version = user_with_session.session.access_token_version

        await AuthService.reset_password(
            test_db,
            ResetPasswordRequest(
                identifier=user.email,
                reset_token=raw_token,
                new_password=NEW_PASSWORD,
            ),
        )

        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_with_session.session.access_token_version == old_version + 1
        assert user_with_session.session.refresh_token_hash is None
        assert user_with_session.session.refresh_token_expires_at is None
        assert user_with_session.session.refresh_token_family is None

    async def test_unknown_identifier_raises_invalid_credentials(self, test_db):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier="nobody@example.com",
                    reset_token=FAKE_RESET_TOKEN,
                    new_password=NEW_PASSWORD,
                ),
            )

    async def test_expired_token_raises_expired_error(self, test_db):
        user, raw_token = await make_user_with_reset_token(test_db, expired=True)

        with pytest.raises(ExpiredResetPasswordTokenError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier=user.email,
                    reset_token=raw_token,
                    new_password=NEW_PASSWORD,
                ),
            )

    async def test_null_expiry_raises_expired_error(self, test_db):
        user = await make_member(test_db, password=CORRECT_PASSWORD)

        with pytest.raises(ExpiredResetPasswordTokenError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier=user.email,
                    reset_token=FAKE_RESET_TOKEN,
                    new_password=NEW_PASSWORD,
                ),
            )

    async def test_wrong_token_raises_invalid_token_error(self, test_db):
        user, _ = await make_user_with_reset_token(test_db)

        with pytest.raises(InvalidResetPasswordTokenError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier=user.email,
                    reset_token="completely_wrong_token",
                    new_password=NEW_PASSWORD,
                ),
            )

    async def test_token_cannot_be_reused_after_successful_reset(self, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
        request = ResetPasswordRequest(
            identifier=user.email,
            reset_token=raw_token,
            new_password=NEW_PASSWORD,
        )

        await AuthService.reset_password(test_db, request)

        with pytest.raises(ExpiredResetPasswordTokenError):
            await AuthService.reset_password(test_db, request)


# tests/unit/email/test_email_content_remaining.py
# Tests for all email content functions not covered in test_email_activation.py

import urllib.parse
from unittest.mock import AsyncMock

import pytest

from src.core.config import settings
from src.utils.email import (
    build_invite_email,
    build_reset_password_email,
    send_account_activation_email,
    send_account_deactivation_email,
    send_admin_email_override_notification,
    send_already_registered_email,
    send_email_change_verification,
    send_forgot_password_email,
    send_password_changed_confirmation,
)
from tests.constants import FAKE_EMAIL, FAKE_INVITE_TOKEN, FAKE_RESET_TOKEN


# ===========================================================================
# TestBuildInviteEmail
# ===========================================================================


class TestBuildInviteEmail:
    def test_returns_tuple_of_three_strings(self):
        result = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(s, str) for s in result)

    def test_subject_is_non_empty(self):
        subject, _, _ = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert len(subject) > 5

    def test_token_appears_in_html(self):
        _, html, _ = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert FAKE_INVITE_TOKEN in html

    def test_token_appears_in_text(self):
        _, _, text = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert FAKE_INVITE_TOKEN in text

    def test_email_is_url_encoded_in_link(self):
        email_with_plus = "user+tag@example.com"
        _, html, text = build_invite_email(FAKE_INVITE_TOKEN, email_with_plus)

        encoded = urllib.parse.quote(email_with_plus)

        assert encoded in html
        assert encoded in text
        # Raw email with + must NOT appear unencoded in the URL
        assert f"&email={email_with_plus}" not in html

    def test_both_token_and_email_in_activation_link(self):
        _, html, text = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        encoded_email = urllib.parse.quote(FAKE_EMAIL)

        assert f"token={FAKE_INVITE_TOKEN}" in html
        assert f"email={encoded_email}" in html
        assert f"token={FAKE_INVITE_TOKEN}" in text
        assert f"email={encoded_email}" in text

    def test_app_url_in_link(self):
        _, html, text = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert settings.APP_URL in html
        assert settings.APP_URL in text

    def test_expiry_hours_mentioned(self):
        _, html, text = build_invite_email(FAKE_INVITE_TOKEN, FAKE_EMAIL)

        assert str(settings.INVITE_TOKEN_EXPIRES_HOURS) in html
        assert str(settings.INVITE_TOKEN_EXPIRES_HOURS) in text

    def test_different_tokens_produce_different_content(self):
        _, html_a, text_a = build_invite_email("token_aaa", FAKE_EMAIL)
        _, html_b, text_b = build_invite_email("token_bbb", FAKE_EMAIL)

        assert html_a != html_b
        assert text_a != text_b


# ===========================================================================
# TestBuildResetPasswordEmail
# ===========================================================================


class TestBuildResetPasswordEmail:
    def test_returns_tuple_of_three_strings(self):
        result = build_reset_password_email(FAKE_RESET_TOKEN)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(s, str) for s in result)

    def test_subject_is_non_empty(self):
        subject, _, _ = build_reset_password_email(FAKE_RESET_TOKEN)

        assert len(subject) > 5

    def test_token_in_html_body(self):
        _, html, _ = build_reset_password_email(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in html

    def test_token_in_text_body(self):
        _, _, text = build_reset_password_email(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in text

    def test_app_url_in_html(self):
        _, html, _ = build_reset_password_email(FAKE_RESET_TOKEN)

        assert settings.APP_URL in html

    def test_expiry_minutes_in_html(self):
        _, html, _ = build_reset_password_email(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in html

    def test_expiry_minutes_in_text(self):
        _, _, text = build_reset_password_email(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in text

    def test_different_tokens_produce_different_content(self):
        _, html_a, text_a = build_reset_password_email("token_aaa")
        _, html_b, text_b = build_reset_password_email("token_bbb")

        assert html_a != html_b
        assert text_a != text_b


# ===========================================================================
# TestSendAlreadyRegisteredEmail
# ===========================================================================


class TestSendAlreadyRegisteredEmail:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_already_registered_email(FAKE_EMAIL)

        mock_send.assert_awaited_once()
        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_contains_forgot_password_link(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_already_registered_email(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert settings.APP_URL in kwargs["html_body"]
        assert settings.APP_URL in kwargs["text_body"]

    async def test_does_not_contain_any_token(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_already_registered_email(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        # This is a notification email — no tokens should appear
        assert "token=" not in kwargs["html_body"]
        assert "token=" not in kwargs["text_body"]

    async def test_subject_is_non_empty(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_already_registered_email(FAKE_EMAIL)

        subject = mock_send.call_args.kwargs["subject"]
        assert len(subject) > 5

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_already_registered_email(FAKE_EMAIL)

        assert mock_send.await_count == 1


# ===========================================================================
# TestSendForgotPasswordEmail
# ===========================================================================


class TestSendForgotPasswordEmail:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_forgot_password_email(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_token_in_html_body(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_forgot_password_email(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in mock_send.call_args.kwargs["html_body"]

    async def test_token_in_text_body(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_forgot_password_email(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in mock_send.call_args.kwargs["text_body"]

    async def test_expiry_minutes_in_html(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_forgot_password_email(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert (
            str(settings.RESET_PASSWORD_EXPIRES_MINUTES)
            in (mock_send.call_args.kwargs["html_body"])
        )

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_forgot_password_email(FAKE_EMAIL, FAKE_RESET_TOKEN)

        assert mock_send.await_count == 1


# ===========================================================================
# TestSendPasswordChangedConfirmation
# ===========================================================================


class TestSendPasswordChangedConfirmation:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_password_changed_confirmation(FAKE_EMAIL)

        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_contains_no_token_or_link(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_password_changed_confirmation(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        # Pure notification — no actionable links
        assert "token=" not in kwargs["html_body"]
        assert "token=" not in kwargs["text_body"]

    async def test_subject_is_non_empty(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_password_changed_confirmation(FAKE_EMAIL)

        assert len(mock_send.call_args.kwargs["subject"]) > 5

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_password_changed_confirmation(FAKE_EMAIL)

        assert mock_send.await_count == 1


# ===========================================================================
# TestSendEmailChangeVerification
# ===========================================================================


class TestSendEmailChangeVerification:
    async def test_sent_to_new_email_not_old(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        new_email = "new_address@example.com"
        code = "123456"

        await send_email_change_verification(new_email, code)

        assert mock_send.call_args.kwargs["to_email"] == new_email

    async def test_code_in_html_body(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        code = "654321"
        await send_email_change_verification(FAKE_EMAIL, code)

        assert code in mock_send.call_args.kwargs["html_body"]

    async def test_code_in_text_body(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        code = "654321"
        await send_email_change_verification(FAKE_EMAIL, code)

        assert code in mock_send.call_args.kwargs["text_body"]

    async def test_expiry_minutes_mentioned(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_email_change_verification(FAKE_EMAIL, "111111")

        kwargs = mock_send.call_args.kwargs
        assert str(settings.ACTIVATION_CODE_EXPIRES_MINUTES) in kwargs["html_body"]

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_email_change_verification(FAKE_EMAIL, "000000")

        assert mock_send.await_count == 1

    async def test_different_codes_produce_different_content(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_email_change_verification(FAKE_EMAIL, "111111")
        html_a = mock_send.call_args.kwargs["html_body"]

        await send_email_change_verification(FAKE_EMAIL, "999999")
        html_b = mock_send.call_args.kwargs["html_body"]

        assert html_a != html_b


# ===========================================================================
# TestSendAccountDeactivationEmail
# ===========================================================================


class TestSendAccountDeactivationEmail:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_deactivation_email(FAKE_EMAIL)

        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_contains_no_reset_link_or_token(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_deactivation_email(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert "token=" not in kwargs["html_body"]
        assert "token=" not in kwargs["text_body"]

    async def test_subject_is_non_empty(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_deactivation_email(FAKE_EMAIL)

        assert len(mock_send.call_args.kwargs["subject"]) > 5

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_deactivation_email(FAKE_EMAIL)

        assert mock_send.await_count == 1


# ===========================================================================
# TestSendAccountActivationEmail
# ===========================================================================


class TestSendAccountActivationEmail:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_email(FAKE_EMAIL)

        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_contains_login_link(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_email(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert settings.APP_URL in kwargs["html_body"]
        assert settings.APP_URL in kwargs["text_body"]

    async def test_contains_no_token(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_email(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert "token=" not in kwargs["html_body"]
        assert "token=" not in kwargs["text_body"]

    async def test_subject_is_non_empty(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_email(FAKE_EMAIL)

        assert len(mock_send.call_args.kwargs["subject"]) > 5

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_account_activation_email(FAKE_EMAIL)

        assert mock_send.await_count == 1


# ===========================================================================
# TestSendAdminEmailOverrideNotification
# ===========================================================================


class TestSendAdminEmailOverrideNotification:
    async def test_calls_send_with_correct_recipient(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_admin_email_override_notification(FAKE_EMAIL)

        assert mock_send.call_args.kwargs["to_email"] == FAKE_EMAIL

    async def test_contains_no_token_or_reset_link(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_admin_email_override_notification(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert "token=" not in kwargs["html_body"]
        assert "token=" not in kwargs["text_body"]

    async def test_subject_is_non_empty(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_admin_email_override_notification(FAKE_EMAIL)

        assert len(mock_send.call_args.kwargs["subject"]) > 5

    async def test_called_exactly_once(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_admin_email_override_notification(FAKE_EMAIL)

        assert mock_send.await_count == 1

    async def test_html_and_text_both_present(self, mocker):
        mock_send = mocker.patch(
            "src.utils.email._send",
            new_callable=AsyncMock,
        )

        await send_admin_email_override_notification(FAKE_EMAIL)

        kwargs = mock_send.call_args.kwargs
        assert len(kwargs["html_body"]) > 0
        assert len(kwargs["text_body"]) > 0
