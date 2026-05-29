from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import structlog.testing
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import CreateResetPasswordRequest, ResetPasswordRequest
from src.auth.service import AuthService
from src.core.config import settings
from src.core.security import generate_reset_password_token, hash_password
from src.users.repository import UserRepositoryBase
from src.utils.email import (
    _reset_password_html,
    _reset_password_text,
    send_reset_password_token,
)
from src.utils.exceptions import (
    ExpiredResetPasswordTokenError,
    InvalidCredentialsError,
    InvalidResetPasswordTokenError,
)
from tests.constants import (
    CORRECT_PASSWORD,
    FAKE_EMAIL,
    FAKE_RESET_TOKEN,
    NEW_PASSWORD,
)
from tests.conftest import make_auth_header, make_member
from tests.factories import make_user_with_reset_token


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
        """
        The raw token (not its hash) must appear in both bodies — it is what
        the frontend extracts from the link and sends to /reset_password.
        """
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
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        )

        await AuthService.create_reset_password_request(
            test_db,
            CreateResetPasswordRequest(identifier=user.email),
        )

        # Give the event loop a chance to schedule the task
        import asyncio

        await asyncio.sleep(0)

        mock_email.assert_awaited_once()
        assert mock_email.call_args.args[0] == user.email

    async def test_does_not_raise_for_unknown_identifier(self, test_db):
        """
        create_reset_password_request must never reveal whether an identifier
        exists — it silently does nothing for unknown users.
        """
        with patch(
            "src.utils.email.send_reset_password_token",
            new_callable=AsyncMock,
        ):
            # must not raise
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

        assert any(l["event"] == "reset_password_request_created" for l in logs)

    async def test_logs_info_not_warning_for_unknown_user(self, test_db):
        """
        Unknown identifier is expected noise on a public endpoint — must
        log at info level, not warning.
        """
        with structlog.testing.capture_logs() as logs:
            await AuthService.create_reset_password_request(
                test_db,
                CreateResetPasswordRequest(identifier="nobody@example.com"),
            )

        failed_logs = [
            l for l in logs if l["event"] == "reset_password_request_creation_failed"
        ]
        assert failed_logs, "Expected a log event for unknown identifier"
        assert all(l["log_level"] == "info" for l in failed_logs)


class TestResetPasswordService:
    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_valid_token_clears_reset_token_fields(self, test_db):
        """
        After a successful reset the token must be consumed — reuse within
        the expiry window must not be possible.
        """
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

    @pytest.mark.asyncio
    async def test_valid_token_invalidates_existing_sessions(self, test_db):
        """
        access_token_version must be incremented and refresh token cleared
        so all existing sessions are invalidated after a password reset.
        """
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

    @pytest.mark.asyncio
    async def test_unknown_identifier_raises_invalid_credentials(self, test_db):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier="nobody@example.com",
                    reset_token=FAKE_TOKEN,
                    new_password=NEW_PASSWORD,
                ),
            )

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_null_expiry_raises_expired_error(self, test_db):
        """
        A user with no expiry set (reset never requested) must be treated
        as expired, not as an invalid token — matches the service branch order.
        """
        user = await make_member(test_db, password=CORRECT_PASSWORD)

        with pytest.raises(ExpiredResetPasswordTokenError):
            await AuthService.reset_password(
                test_db,
                ResetPasswordRequest(
                    identifier=user.email,
                    reset_token=FAKE_TOKEN,
                    new_password=NEW_PASSWORD,
                ),
            )

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_token_cannot_be_reused_after_successful_reset(self, test_db):
        """
        Using the same token a second time must fail — the first successful
        reset must have cleared the token from the session.
        """
        user, raw_token = await make_user_with_reset_token(test_db)
        request = ResetPasswordRequest(
            identifier=user.email,
            reset_token=raw_token,
            new_password=NEW_PASSWORD,
        )

        await AuthService.reset_password(test_db, request)

        with pytest.raises(ExpiredResetPasswordTokenError):
            await AuthService.reset_password(test_db, request)
