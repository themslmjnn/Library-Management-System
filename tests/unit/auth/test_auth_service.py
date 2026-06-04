import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import (
    ActivateAccountWithCode,
    ActivateAccountWithToken,
    CreateRefreshTokenRequest,
    ForgotPasswordPublicRequest,
)
from src.auth.service import AuthService
from src.core.security import create_refresh_token, decode_access_token
from src.users.models import UserRole
from src.users.repository import UserRepositoryBase
from src.utils.custom_exceptions import (
    AccountInactiveError,
    AccountLockedError,
    EmptyCredentialsError,
    ExpiredActivationCodeError,
    ExpiredInviteTokenError,
    ExpiredRefreshTokenError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    InvalidInviteTokenError,
    InvalidRefreshTokenError,
)
from src.utils.response_messages import PublicMessages
from src.utils.response_schemas import MessageResponse
from tests.constants import (
    CORRECT_PASSWORD,
    DEFAULT_PASSWORD,
    NEW_PASSWORD,
    WRONG_PASSWORD,
)
from tests.factories import (
    make_invited_user,
    make_member,
    make_user_with_activation_code,
    make_user_with_refresh_token,
)


class _MockForm:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password


def _form(username: str | None = None, password: str | None = None) -> _MockForm:
    return _MockForm(username, password)


class TestLogin:
    async def test_raise_error_for_empty_username(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        with pytest.raises(EmptyCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form(None, DEFAULT_PASSWORD)
            )

    async def test_raise_error_for_empty_password(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        with pytest.raises(EmptyCredentialsError):
            await AuthService.login(test_db, mock_response, _form("test_user", None))

    async def test_login_fails_user_not_found(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form("nobody@gmail.com", WRONG_PASSWORD)
            )

    async def test_login_blocked_when_account_locked(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        user_session.session.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=15
        )

        await test_db.commit()

        with pytest.raises(AccountLockedError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, CORRECT_PASSWORD)
            )

    async def test_locked_account_allows_login_after_expiry(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        user_session.session.locked_until = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )

        await test_db.commit()

        result = await AuthService.login(
            test_db, mock_response, _form(user.email, CORRECT_PASSWORD)
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert "access_token" in result
        assert user_session.session.failed_login_attempts == 0
        assert user_session.session.locked_until is None

    async def test_login_fails_no_password_set(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            has_password=False,
            is_active=False,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, DEFAULT_PASSWORD)
            )

    async def test_login_increments_failed_attempts(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, WRONG_PASSWORD)
            )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.failed_login_attempts == 1

    async def test_login_locks_account_after_max_attempts(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        user_session.session.failed_login_attempts = 4

        await test_db.commit()

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, WRONG_PASSWORD)
            )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.failed_login_attempts == 5
        assert user_session.session.locked_until is not None
        assert user_session.session.locked_until > datetime.now(timezone.utc)

    async def test_login_fails_wrong_password(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, WRONG_PASSWORD)
            )

    async def test_login_fails_inactive_account(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            is_active=False,
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(AccountInactiveError):
            await AuthService.login(
                test_db, mock_response, _form(user.email, CORRECT_PASSWORD)
            )

    async def test_reset_failed_attempts_on_successful_login(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=DEFAULT_PASSWORD,
        )
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        user_session.session.failed_login_attempts = 3

        await test_db.commit()

        await AuthService.login(
            test_db, mock_response, _form(user.email, DEFAULT_PASSWORD)
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.failed_login_attempts == 0
        assert user_session.session.locked_until is None

    async def test_login_error_message_is_identical_for_unknown_and_wrong_password(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        await make_member(
            test_db,
            email="exists@gmail.com",
            password=CORRECT_PASSWORD,
        )

        try:
            await AuthService.login(
                test_db, mock_response, _form("exists@gmail.com", WRONG_PASSWORD)
            )
        except InvalidCredentialsError as e:
            known_email_error = e.detail

        try:
            await AuthService.login(
                test_db, mock_response, _form("nobody@gmail.com", WRONG_PASSWORD)
            )
        except InvalidCredentialsError as e:
            unknown_email_error = e.detail

        assert known_email_error == unknown_email_error

    async def test_login_does_not_increment_access_token_version(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        original_version = user_session.session.access_token_version

        await AuthService.login(
            test_db, mock_response, _form(user.email, CORRECT_PASSWORD)
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.access_token_version == original_version

    async def test_login_sets_new_refresh_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        await AuthService.login(
            test_db, mock_response, _form(user.email, CORRECT_PASSWORD)
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.refresh_token_hash is not None
        assert user_session.session.refresh_token_expires_at is not None
        assert user_session.session.refresh_token_family is not None

    async def test_successful_login_with_email(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        await make_member(
            test_db,
            email="test@gmail.com",
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(
            test_db, mock_response, _form("test@gmail.com", DEFAULT_PASSWORD)
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_successful_login_with_username(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        await make_member(
            test_db,
            username="testuser",
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(
            test_db, mock_response, _form("testuser", DEFAULT_PASSWORD)
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_successful_login_with_phone_number(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        await make_member(
            test_db,
            phone_number="+992 000 111 222",
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(
            test_db, mock_response, _form("+992 000 111 222", DEFAULT_PASSWORD)
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"


class TestLogout:
    async def test_logout_clears_refresh_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(test_db)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        user_session.session.refresh_token_hash = "some_hash"
        user_session.session.refresh_token_family = "some_family"
        user_session.session.refresh_token_expires_at = datetime.now(
            timezone.utc
        ) + timedelta(days=7)

        await test_db.commit()

        await AuthService.logout(test_db, mock_response, user.id)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.refresh_token_hash is None
        assert user_session.session.refresh_token_family is None
        assert user_session.session.refresh_token_expires_at is None

        mock_response.delete_cookie.assert_any_call(
            key="refresh_token",
            path="/auth/refresh_token",
        )

        mock_response.delete_cookie.assert_any_call(
            key="refresh_token_family",
            path="/auth/refresh_token",
        )

    async def test_invalidate_user_with_no_refresh_token(
        self, test_db, mock_response: MagicMock
    ):
        user = await make_member(test_db)

        await AuthService.logout(test_db, mock_response, user.id)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.refresh_token_hash is None
        assert user_session.session.refresh_token_family is None
        assert user_session.session.refresh_token_expires_at is None

    async def test_logout_increments_token_version(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user = await make_member(test_db)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        original_version = user_session.session.access_token_version

        await AuthService.logout(test_db, mock_response, user.id)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.access_token_version == original_version + 1


class TestActivateAccountWithToken:
    async def test_activation_fails_user_not_found(self, test_db: AsyncSession):
        request = ActivateAccountWithToken(
            email="nobody@gmail.com",
            invite_token="MagicMock_token",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_fails_no_pending_token(self, test_db):
        user = await make_member(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="MagicMock_token",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_fails_expired_token(self, test_db: AsyncSession):
        user, raw_invite_token = await make_invited_user(test_db)

        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )

        user_activation.activation.invite_token_expires_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=1)

        await test_db.commit()

        activation_request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_invite_token,
            password=NEW_PASSWORD,
        )

        with pytest.raises(ExpiredInviteTokenError):
            await AuthService.activate_account_with_token(test_db, activation_request)

    async def test_activation_fails_wrong_token(self, test_db: AsyncSession):
        user, _ = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="2787daa7fed0ac356ac8ce76c0e37079a033e47cdc929b04a2bbb195ea4361d5",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_succeeds(self, test_db: AsyncSession):
        user, raw_invite_token = await make_invited_user(
            test_db,
            role=UserRole.member,
        )

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_invite_token,
            password=NEW_PASSWORD,
        )

        await AuthService.activate_account_with_token(test_db, request)

        await test_db.refresh(user)
        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )

        assert user.is_active is True
        assert user.password_hash is not None
        assert user_activation.activation.invite_token_hash is None
        assert user_activation.activation.invite_token_expires_at is None

    async def test_token_is_single_use(self, test_db: AsyncSession):
        user, raw_invite_token = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_invite_token,
            password=NEW_PASSWORD,
        )

        await AuthService.activate_account_with_token(test_db, request)

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

        assert user.is_active is True


class TestActivateAccountWithCode:
    async def test_activation_fails_user_not_found(self, test_db):
        request = ActivateAccountWithCode(
            email="nobody@gmail.com",
            code="MagicMockcode",
        )

        with pytest.raises(InvalidActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

    async def test_activation_fails_expired_code(self, test_db: AsyncSession):
        user, raw_code = await make_user_with_activation_code(test_db)

        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )

        user_activation.activation.account_activation_code_expires_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=1)

        await test_db.commit()

        request = ActivateAccountWithCode(
            email=user.email,
            code=raw_code,
        )

        with pytest.raises(ExpiredActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

    async def test_activation_fails_wrong_code(self, test_db: AsyncSession):
        user, _ = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(
            email=user.email,
            code="wrongcode",
        )

        with pytest.raises(InvalidActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

    async def test_activation_succeeds(self, test_db: AsyncSession):
        user, raw_code = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(
            email=user.email,
            code=raw_code,
        )

        await AuthService.activate_account_with_code(test_db, request)

        await test_db.refresh(user)
        user_activation = await UserRepositoryBase.get_user_by_id_with_activation(
            test_db, user.id
        )

        assert user.is_active is True
        assert user_activation.activation.account_activation_code_hash is None
        assert user_activation.activation.account_activation_code_expires_at is None

    async def test_code_is_single_use(self, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(
            email=user.email,
            code=raw_code,
        )

        await AuthService.activate_account_with_code(test_db, request)

        with pytest.raises(InvalidActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

        assert user.is_active is True


class TestRefreshToken:
    async def test_refresh_fails_invalid_jwt(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        new_family = secrets.token_urlsafe(32)
        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(
                test_db, mock_response, "not.a.valid.jwt", new_family
            )

    async def test_refresh_fails_user_not_found(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        raw_refresh_token, _ = create_refresh_token(
            CreateRefreshTokenRequest(
                user_id=99999,
                family="test_family",
            )
        )
        new_family = secrets.token_urlsafe(32)

        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(
                test_db, mock_response, raw_refresh_token, new_family
            )

    async def test_refresh_fails_no_stored_hash(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        new_family = secrets.token_urlsafe(32)

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        user_session.session.refresh_token_hash = None

        await test_db.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(
                test_db, mock_response, raw_refresh, new_family
            )

    async def test_refresh_fails_expired_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        user_session.session.refresh_token_expires_at = datetime.now(
            timezone.utc
        ) - timedelta(seconds=1)

        await test_db.commit()

        new_family = secrets.token_urlsafe(32)

        with pytest.raises(ExpiredRefreshTokenError):
            await AuthService.refresh_token(
                test_db, mock_response, raw_refresh, new_family
            )

    async def test_reject_wrong_refresh_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        new_family = secrets.token_urlsafe(32)

        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(
                test_db, mock_response, "wrong_refresh_token", new_family
            )

    async def test_refresh_issues_new_access_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)

        result = await AuthService.refresh_token(
            test_db, mock_response, raw_refresh, "test_family_abc"
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_refresh_rotates_refresh_token(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        old_hash = user_session.session.refresh_token_hash
        old_family = user_session.session.refresh_token_family

        await AuthService.refresh_token(
            test_db, mock_response, raw_refresh, "test_family_abc"
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.refresh_token_hash != old_hash
        assert user_session.session.refresh_token_family != old_family

    async def test_refresh_does_not_increment_token_version(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        original_version = user_session.session.access_token_version

        await AuthService.refresh_token(
            test_db, mock_response, raw_refresh, "test_family_abc"
        )

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )

        assert user_session.session.access_token_version == original_version

    async def test_refresh_embeds_correct_access_token_version(
        self, test_db: AsyncSession, mock_response: MagicMock
    ):
        user, raw_refresh = await make_user_with_refresh_token(test_db)

        result = await AuthService.refresh_token(
            test_db, mock_response, raw_refresh, "test_family_abc"
        )

        payload = decode_access_token(result["access_token"])

        user_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        assert payload["version"] == user_session.session.access_token_version


# Tests for reseting password for unauthenticated users
# Done
class TestForgotPasswordPublic:
    """
    Forgot password is enumeration-protected — always returns the same
    MessageResponse regardless of whether the user exists or not.
    The only observable difference is whether the email was sent and
    whether the reset token was written to the session.
    """

    async def test_returns_message_response_when_user_found(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username=user.username,
            phone_number=user.phone_number,
        )

        result = await AuthService.create_forgot_passsword_request(test_db, request)

        assert isinstance(result, MessageResponse)
        assert result.detail == PublicMessages.FORGOT_PASSWORD

    async def test_returns_same_message_response_when_user_not_found(
        self, test_db: AsyncSession
    ):
        request = ForgotPasswordPublicRequest(
            username="nonexistent_user",
            phone_number="+15550000099",
        )

        result = await AuthService.create_forgot_passsword_request(test_db, request)

        assert isinstance(result, MessageResponse)
        assert result.detail == PublicMessages.FORGOT_PASSWORD

    async def test_reset_token_written_to_session_when_user_found(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username=user.username,
            phone_number=user.phone_number,
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.reset_password_token_hash is not None
        assert session.reset_password_token_expires_at is not None
        assert session.reset_password_token_expires_at > datetime.now(timezone.utc)

    async def test_reset_token_not_written_when_user_not_found(
        self, test_db: AsyncSession
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username="nonexistent_user",
            phone_number="+15550000099",
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.reset_password_token_hash is None
        assert session.reset_password_token_expires_at is None

    async def test_send_forgot_password_email_called_when_user_found(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username=user.username,
            phone_number=user.phone_number,
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        await asyncio.sleep(0)

        call_args = mock_send_forgot_password_email.call_args

        mock_send_forgot_password_email.assert_called_once()
        assert call_args.args[0] == user.email

    async def test_send_forgot_password_email_not_called_when_user_not_found(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        request = ForgotPasswordPublicRequest(
            username="nonexistent_user",
            phone_number="+15550000099",
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        await asyncio.sleep(0)

        mock_send_forgot_password_email.assert_not_called()

    async def test_username_matches_but_phone_number_does_not_takes_no_action(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username=user.username,
            phone_number="+15559999999",
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        await asyncio.sleep(0)

        mock_send_forgot_password_email.assert_not_called()

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        assert user_with_session.session.reset_password_token_hash is None
        assert user_with_session.session.refresh_token_expires_at is None

    async def test_phone_number_matches_but_username_does_not_takes_no_action(
        self, test_db: AsyncSession, mock_send_forgot_password_email
    ):
        user = await make_member(test_db)

        request = ForgotPasswordPublicRequest(
            username="wrong_username",
            phone_number=user.phone_number,
        )

        await AuthService.create_forgot_passsword_request(test_db, request)

        await asyncio.sleep(0)

        mock_send_forgot_password_email.assert_not_called()

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )

        assert user_with_session.session.reset_password_token_hash is None
        assert user_with_session.session.reset_password_token_expires_at is None
