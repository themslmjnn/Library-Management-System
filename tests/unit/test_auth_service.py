from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import (
    ActivateAccountWithCode,
    ActivateAccountWithToken,
    CreateRefreshTokenRequest,
)
from src.auth.service import AuthService
from src.core.security import (
    create_refresh_token,
    generate_account_activation_code,
    generate_invite_token,
    hash_password,
)
from src.user.models import UserRole
from src.utils.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    ExpiredActivationCodeError,
    ExpiredInviteTokenError,
    ExpiredRefreshTokenError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    InvalidInviteTokenError,
    InvalidRefreshTokenError,
)
from tests.factories import (
    make_invited_user,
    make_member,
    make_user,
    make_user_with_activation_code,
)
from src.core.dependencies import CurrentUser

DEFAULT_PASSWORD = "Valid123!"
CORRECT_PASSWORD = "Correct123!"
WRONG_PASSWORD = "Wrong123!"
NEW_PASSWORD = "NewPassword123!"


# LOGIN
class TestLogin:
    async def test_successful_login_with_email(self, test_db: AsyncSession, mock_response: Any) -> None:
        user = await make_member(
            test_db, 
            email="test@gmail.com", 
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(test_db, mock_response, _form("test@gmail.com", DEFAULT_PASSWORD))

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert user.refresh_token_hash is not None
        assert user.refresh_token_expires_at is not None
        assert user.refresh_token_family is not None


    async def test_successful_login_with_username(self, test_db: AsyncSession, mock_response: Any) -> None:
        user = await make_member(
            test_db, 
            username="testuser", 
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(test_db, mock_response, _form("testuser", DEFAULT_PASSWORD))

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert user.refresh_token_hash is not None
        assert user.refresh_token_expires_at is not None
        assert user.refresh_token_family is not None


    async def test_successful_login_with_phone_number(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            phone_number="+992 000 111 222", 
            password=DEFAULT_PASSWORD,
        )

        result = await AuthService.login(test_db, mock_response, _form("+992 000 111 222", DEFAULT_PASSWORD))

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert user.refresh_token_hash is not None
        assert user.refresh_token_expires_at is not None
        assert user.refresh_token_family is not None


    async def test_login_error_message_is_identical_for_unknown_and_wrong_password(
        self, test_db, mock_response
    ):
        await make_member(test_db, email="exists@gmail.com", password=CORRECT_PASSWORD)

        try:
            await AuthService.login(test_db, mock_response, _form("exists@gmail.com", WRONG_PASSWORD))
        except InvalidCredentialsError as e:
            known_email_error = e.detail

        try:
            await AuthService.login(test_db, mock_response, _form("nobody@gmail.com", WRONG_PASSWORD))
        except InvalidCredentialsError as e:
            unknown_email_error = e.detail

        assert known_email_error == unknown_email_error


    async def test_login_fails_user_not_found(self, test_db: AsyncSession, mock_response: Any) -> None:
        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form("nobody@gmail.com", "pass"))


    async def test_login_fails_wrong_password(self, test_db: AsyncSession, mock_response: Any) -> None:
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, WRONG_PASSWORD))


    async def test_login_increments_failed_attempts(self, test_db: AsyncSession, mock_response: Any) -> None:
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, WRONG_PASSWORD))

        await test_db.refresh(user)

        assert user.failed_login_attempts == 1


    async def test_login_locks_account_after_max_attempts(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        user.failed_login_attempts = 4

        await test_db.commit()

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, WRONG_PASSWORD))

        await test_db.refresh(user)

        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)


    async def test_login_blocked_when_account_locked(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

        await test_db.commit()

        with pytest.raises(AccountLockedError):
            await AuthService.login(test_db, mock_response, _form(user.email, CORRECT_PASSWORD))


    async def test_reset_failed_attempts_on_successful_login(self, test_db: AsyncSession, mock_response: Any) -> None:
        user = await make_member(
            test_db, 
            password=DEFAULT_PASSWORD,
        )

        user.failed_login_attempts = 3

        await test_db.commit()

        await AuthService.login(test_db, mock_response, _form(user.email, DEFAULT_PASSWORD))

        await test_db.refresh(user)

        assert user.failed_login_attempts == 0
        assert user.locked_until is None


    async def test_login_fails_no_password_set(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            has_password=False, 
            is_active=False,
        )

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, DEFAULT_PASSWORD))


    async def test_login_fails_inactive_account(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            is_active=False, 
            password=CORRECT_PASSWORD,
        )

        with pytest.raises(AccountInactiveError):
            await AuthService.login(test_db, mock_response, _form(user.email, CORRECT_PASSWORD))


    async def test_login_does_not_increment_token_version(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        original_version = user.access_token_version

        await AuthService.login(test_db, mock_response, _form(user.email, CORRECT_PASSWORD))

        await test_db.refresh(user)

        assert user.access_token_version == original_version


    async def test_locked_account_allows_login_after_expiry(self, test_db, mock_response):
        user = await make_member(
            test_db, 
            password=CORRECT_PASSWORD,
        )

        user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        await test_db.commit()

        result = await AuthService.login(test_db, mock_response, _form(user.email, CORRECT_PASSWORD))

        await test_db.refresh(user)

        assert "access_token" in result
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


# LOGOUT
class TestLogout:
    async def test_logout_clears_refresh_token(self, test_db: AsyncSession) -> None:
        user = await make_member(test_db)

        user.refresh_token_hash = "some_hash"
        user.refresh_token_family = "some_family"
        user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await test_db.commit()

        user_obj = await test_db.get(type(user), user.id)

        await AuthService._invalidate_all_tokens(test_db, user_obj)

        await test_db.refresh(user)

        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
        assert user.refresh_token_expires_at is None


    async def test_logout_increments_token_version(self, test_db: AsyncSession) -> None:
        user = await make_member(test_db)

        original_version = user.access_token_version

        await AuthService._invalidate_all_tokens(test_db, user)

        await test_db.refresh(user)

        assert user.access_token_version == original_version + 1


# ACTIVATE WITH TOKEN
class TestActivateAccountWithToken:
    async def test_activation_succeeds(self, test_db: AsyncSession) -> None:
        user, raw_token = await make_invited_user(
            test_db, 
            role=UserRole.member,
        )

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password=NEW_PASSWORD,
        )

        await AuthService.activate_account_with_token(test_db, request)

        await test_db.refresh(user)

        assert user.is_active is True
        assert user.password_hash is not None
        assert user.invite_token_hash is None
        assert user.invite_token_expires_at is None


    async def test_activation_fails_wrong_token(self, test_db: AsyncSession) -> None:
        user, _ = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="wrong_token_value",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)


    async def test_activation_fails_expired_token(self, test_db: AsyncSession) -> None:
        user, raw_token = await make_invited_user(test_db)

        user.invite_token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        await test_db.commit()

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password=NEW_PASSWORD,
        )

        with pytest.raises(ExpiredInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)


    async def test_activation_fails_user_not_found(self, test_db: AsyncSession) -> None:
        request = ActivateAccountWithToken(
            email="nobody@gmail.com",
            invite_token="any_token",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)


    async def test_activation_fails_no_pending_token(self, test_db):
        user = await make_member(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="any_token",
            password=NEW_PASSWORD,
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)


    async def test_token_is_single_use(self, test_db: AsyncSession) -> None:
        user, raw_token = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password=NEW_PASSWORD,
        )

        await AuthService.activate_account_with_token(test_db, request)

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)


# ── ACTIVATE WITH CODE ──────────────────────────────────────────────────────────
class TestActivateAccountWithCode:

    async def test_activation_succeeds(self, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(email=user.email, code=raw_code)

        await AuthService.activate_account_with_code(test_db)

        await test_db.refresh(user)
        assert user.is_active is True
        assert user.account_activation_code_hash is None
        assert user.account_activation_code_expires_at is None

    async def test_activation_fails_wrong_code(self, test_db):
        user, _ = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(email=user.email, code="wrongcode")

        with pytest.raises(InvalidActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

    async def test_activation_fails_expired_code(self, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)
        user.account_activation_code_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_db.commit()

        request = ActivateAccountWithCode(email=user.email, code=raw_code)

        with pytest.raises(ExpiredActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)

    async def test_code_is_single_use(self, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)

        request = ActivateAccountWithCode(email=user.email, code=raw_code)
        await AuthService.activate_account_with_code(test_db, request)

        with pytest.raises(InvalidActivationCodeError):
            await AuthService.activate_account_with_code(test_db, request)


# ── REFRESH TOKEN ───────────────────────────────────────────────────────────────

class TestRefreshToken:

    async def test_refresh_issues_new_access_token(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)

        result = await AuthService.refresh_token(test_db, mock_response, raw_refresh)

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_refresh_rotates_refresh_token(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        old_hash = user.refresh_token_hash
        old_family = user.refresh_token_family

        await AuthService.refresh_token(test_db, mock_response, raw_refresh)

        await test_db.refresh(user)
        assert user.refresh_token_hash != old_hash
        assert user.refresh_token_family != old_family

    async def test_refresh_fails_invalid_jwt(self, test_db, mock_response):
        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(test_db, mock_response, "not.a.valid.jwt")

    async def test_refresh_fails_expired_token(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        user.refresh_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await test_db.commit()

        with pytest.raises(ExpiredRefreshTokenError):
            await AuthService.refresh_token(test_db, mock_response, raw_refresh)

    async def test_refresh_fails_no_stored_hash(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        user.refresh_token_hash = None
        await test_db.commit()

        with pytest.raises(InvalidRefreshTokenError):
            await AuthService.refresh_token(test_db, mock_response, raw_refresh)

    async def test_reuse_detection_invalidates_all_tokens(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        original_version = user.access_token_version

        # rotate once — old token is now stale
        await AuthService.refresh_token(test_db, mock_response, raw_refresh)

        # use the old token again — reuse detected
        with pytest.raises(Exception):
            await AuthService.refresh_token(test_db, mock_response, raw_refresh)

        await test_db.refresh(user)
        # all tokens must be invalidated
        assert user.access_token_version == original_version + 1
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None

    async def test_refresh_does_not_increment_token_version(self, test_db, mock_response):
        user, raw_refresh = await make_user_with_refresh_token(test_db)
        original_version = user.access_token_version

        await AuthService.refresh_token(test_db, mock_response, raw_refresh)

        await test_db.refresh(user)
        assert user.access_token_version == original_version


class _MockForm:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

def _form(username: str, password: str) -> _MockForm:
    return _MockForm(username, password)


async def make_user_with_refresh_token(test_db: AsyncSession):
    """Create a member with a valid refresh token already stored."""
    user = await make_member(test_db, password="Valid123!")

    raw_refresh, hashed_refresh = create_refresh_token(
        CreateRefreshTokenRequest(
            user_id=user.id,
            family="test_family_abc",
        )
    )

    user.refresh_token_hash = hashed_refresh
    user.refresh_token_family = "test_family_abc"
    user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await test_db.commit()

    return user, raw_refresh