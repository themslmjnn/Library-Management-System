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