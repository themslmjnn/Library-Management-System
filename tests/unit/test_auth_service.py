import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.auth.schemas import ActivateAccountWithToken, ActivateAccountWithCode
from src.user.models import UserRole
from src.utils.exceptions import (
    InvalidCredentialsError,
    AccountLockedError,
    AccountInactiveError,
    InvalidInviteTokenError,
    ExpiredInviteTokenError,
    InvalidActivationCodeError,
    ExpiredActivationCodeError,
    InvalidRefreshTokenError,
    ExpiredRefreshTokenError,
)
from src.core.security import (
    hash_password,
    create_refresh_token,
    generate_invite_token,
    generate_account_activation_code,
)
from src.auth.schemas import CreateRefreshTokenRequest
from tests.factories import (
    make_user,
    make_member,
    make_invited_user,
    make_user_with_activation_code,
)


# ── LOGIN ──────────────────────────────────────────────────────────────────────

class TestLogin:

    async def test_login_success_with_email(self, test_db: AsyncSession, mock_response):
        user = await make_member(test_db, email="test@gmail.com", password="Valid123!")

        result = await AuthService.login(test_db, mock_response, _form("test@gmail.com", "Valid123!"))

        assert "access_token" in result
        assert result["token_type"] == "bearer"

    async def test_login_success_with_username(self, test_db, mock_response):
        user = await make_member(test_db, username="testuser", password="Valid123!")

        result = await AuthService.login(test_db, mock_response, _form("testuser", "Valid123!"))

        assert "access_token" in result

    async def test_login_success_with_phone(self, test_db, mock_response):
        user = await make_member(test_db, phone_number="+15551234567", password="Valid123!")

        result = await AuthService.login(test_db, mock_response, _form("+15551234567", "Valid123!"))

        assert "access_token" in result

    async def test_login_resets_failed_attempts_on_success(self, test_db, mock_response):
        user = await make_member(test_db, password="Valid123!")
        user.failed_login_attempts = 3
        await test_db.commit()

        await AuthService.login(test_db, mock_response, _form(user.email, "Valid123!"))

        await test_db.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    async def test_login_stores_refresh_token_hash(self, test_db, mock_response):
        user = await make_member(test_db, password="Valid123!")

        await AuthService.login(test_db, mock_response, _form(user.email, "Valid123!"))

        await test_db.refresh(user)
        assert user.refresh_token_hash is not None
        assert user.refresh_token_family is not None
        assert user.refresh_token_expires_at is not None

    async def test_login_fails_user_not_found(self, test_db, mock_response):
        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form("nobody@gmail.com", "pass"))

    async def test_login_fails_wrong_password(self, test_db, mock_response):
        user = await make_member(test_db, password="Correct123!")

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, "Wrong123!"))

    async def test_login_increments_failed_attempts(self, test_db, mock_response):
        user = await make_member(test_db, password="Correct123!")

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, "Wrong123!"))

        await test_db.refresh(user)
        assert user.failed_login_attempts == 1

    async def test_login_locks_account_after_max_attempts(self, test_db, mock_response):
        user = await make_member(test_db, password="Correct123!")
        user.failed_login_attempts = 4  # one more will trigger lockout
        await test_db.commit()

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, "Wrong123!"))

        await test_db.refresh(user)
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)

    async def test_login_blocked_when_account_locked(self, test_db, mock_response):
        user = await make_member(test_db, password="Correct123!")
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        await test_db.commit()

        with pytest.raises(AccountLockedError):
            await AuthService.login(test_db, mock_response, _form(user.email, "Correct123!"))

    async def test_locked_account_allows_login_after_expiry(self, test_db, mock_response):
        user = await make_member(test_db, password="Correct123!")
        user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)  # expired
        await test_db.commit()

        result = await AuthService.login(test_db, mock_response, _form(user.email, "Correct123!"))

        assert "access_token" in result

    async def test_login_fails_no_password_set(self, test_db, mock_response):
        # invited user who hasn't activated yet
        user = await make_member(test_db, has_password=False, is_active=False)

        with pytest.raises(InvalidCredentialsError):
            await AuthService.login(test_db, mock_response, _form(user.email, "anything"))

    async def test_login_fails_inactive_account(self, test_db, mock_response):
        user = await make_member(test_db, is_active=False, password="Valid123!")

        with pytest.raises(AccountInactiveError):
            await AuthService.login(test_db, mock_response, _form(user.email, "Valid123!"))

    async def test_login_does_not_increment_token_version(self, test_db, mock_response):
        user = await make_member(test_db, password="Valid123!")
        original_version = user.access_token_version

        await AuthService.login(test_db, mock_response, _form(user.email, "Valid123!"))

        await test_db.refresh(user)
        assert user.access_token_version == original_version

class TestLogout:
    async def test_logout_clears_refresh_token(self, test_db, mock_response):
        user = await make_member(test_db)
        user.refresh_token_hash = "some_hash"
        user.refresh_token_family = "some_family"
        user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        await test_db.commit()

        from dataclasses import dataclass

        @dataclass
        class CurrentUser:
            id: int
            role: UserRole
            is_active: bool

        current_user = CurrentUser(id=user.id, role=user.role, is_active=user.is_active)

        # patch _invalidate_all_tokens to use the real user object
        user_obj = await test_db.get(type(user), user.id)
        await AuthService._invalidate_all_tokens(test_db, user_obj)

        await test_db.refresh(user)
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
        assert user.refresh_token_expires_at is None

    async def test_logout_increments_token_version(self, test_db):
        user = await make_member(test_db)
        original_version = user.access_token_version

        await AuthService._invalidate_all_tokens(test_db, user)

        await test_db.refresh(user)
        assert user.access_token_version == original_version + 1

# ── ACTIVATE WITH TOKEN ─────────────────────────────────────────────────────────

class TestActivateAccountWithToken:

    async def test_activation_succeeds(self, test_db):
        user, raw_token = await make_invited_user(test_db, role=UserRole.member)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password="NewPass123!",
        )

        await AuthService.activate_account_with_token(test_db, request)

        await test_db.refresh(user)
        assert user.is_active is True
        assert user.password_hash is not None
        assert user.invite_token_hash is None
        assert user.invite_token_expires_at is None

    async def test_activation_fails_wrong_token(self, test_db):
        user, _ = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="wrong_token_value",
            password="NewPass123!",
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_fails_expired_token(self, test_db):
        user, raw_token = await make_invited_user(test_db)
        user.invite_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_db.commit()

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password="NewPass123!",
        )

        with pytest.raises(ExpiredInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_fails_user_not_found(self, test_db):
        request = ActivateAccountWithToken(
            email="nobody@gmail.com",
            invite_token="any_token",
            password="NewPass123!",
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_activation_fails_no_pending_token(self, test_db):
        # already activated user — no invite token
        user = await make_member(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token="any_token",
            password="NewPass123!",
        )

        with pytest.raises(InvalidInviteTokenError):
            await AuthService.activate_account_with_token(test_db, request)

    async def test_token_is_single_use(self, test_db):
        user, raw_token = await make_invited_user(test_db)

        request = ActivateAccountWithToken(
            email=user.email,
            invite_token=raw_token,
            password="NewPass123!",
        )

        await AuthService.activate_account_with_token(test_db, request)

        # second activation attempt must fail
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
    """Minimal stand-in for OAuth2PasswordRequestForm."""
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