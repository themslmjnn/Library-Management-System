import asyncio
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import generate_email_change_code
from src.users.models import User
from src.users.repository import UserRepositoryBase
from src.utils.enums import UserRole
from src.utils.response_messages import PublicMessages
from tests.conftest import make_auth_header
from tests.constants import CORRECT_PASSWORD, NEW_PASSWORD, OLD_PASSWORD
from tests.factories import make_member


class TestCreateAccountPublic:
    async def test_creates_user_successfully(
        self, test_db: AsyncSession, client: AsyncClient, mocker
    ):
        mocker.patch(
            "src.users.service.email_sender.build_activation_code_email",
            return_value=("subject", "<html>", "text"),
        )

        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "newuser@gmail.com",
            "phone_number": "+15550001234",
            "date_of_birth": "1990-01-01",
            "password": CORRECT_PASSWORD,
        }

        response = await client.post(
            "/users/register",
            json=payload,
        )

        assert response.status_code == 200
        assert "detail" in response.json()

        user = await UserRepositoryBase.get_user_by_email(test_db, "newuser@gmail.com")

        assert user is not None
        assert user.is_active is False
        assert user.role == UserRole.guest

    async def test_duplicate_email_returns_200_with_same_message(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_already_registered_email,
    ):
        await make_member(
            test_db,
            email="taken@gmail.com",
        )

        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "taken@gmail.com",
            "phone_number": "+15550009999",
            "date_of_birth": "1990-01-01",
            "password": CORRECT_PASSWORD,
        }

        response = await client.post(
            "/users/register",
            json=payload,
        )

        assert response.status_code == 200
        assert response.json()["detail"] == PublicMessages.REGISTRATION

    async def test_already_registered_email_sent_on_duplicate(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_already_registered_email,
    ):
        await make_member(
            test_db,
            email="taken@gmail.com",
        )

        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "taken@gmail.com",
            "phone_number": "+15550009999",
            "date_of_birth": "1990-01-01",
            "password": CORRECT_PASSWORD,
        }

        await client.post(
            "/users/register",
            json=payload,
        )

        await asyncio.sleep(0)

        mock_send_already_registered_email.assert_called_once_with("taken@gmail.com")

    async def test_duplicate_phone_returns_409(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        await make_member(
            test_db,
            phone_number="+15550001111",
        )

        payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "unique@gmail.com",
            "phone_number": "+15550001111",
            "date_of_birth": "1990-01-01",
            "password": CORRECT_PASSWORD,
        }

        response = await client.post(
            "/users/register",
            json=payload,
        )

        assert response.status_code == 409


class TestGetMe:
    async def test_returns_user_detail(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(
            test_db,
            email="test_email@gmail.com",
        )

        headers = await make_auth_header(test_db, user)

        response = await client.get(
            "/users/me",
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert data["id"] == user.id
        assert data["email"] == "test_email@gmail.com"

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users/me")

        assert response.status_code == 401


class TestUpdateMyPassword:
    async def test_successfully_updates_password(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_password_changed_confirmation,
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        update_request = {
            "old_password": OLD_PASSWORD,
            "new_password": NEW_PASSWORD,
        }

        headers = await make_auth_header(test_db, user)

        response = await client.put(
            "/users/me/password",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 204

    async def test_reject_incorrect_old_password(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )

        update_request = {
            "old_password": "IncorrectOldPassword123!",
            "new_password": NEW_PASSWORD,
        }

        headers = await make_auth_header(test_db, user)

        response = await client.put(
            "/users/me/password", json=update_request, headers=headers
        )

        assert response.status_code == 400

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.put("/users/me/password")

        assert response.status_code == 401

    async def test_password_change_sends_confirmation_email(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_password_changed_confirmation,
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )
        headers = await make_auth_header(test_db, user)

        await client.put(
            "/users/me/password",
            json={
                "old_password": OLD_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )

        await asyncio.sleep(0)

        mock_send_password_changed_confirmation.assert_called_once_with(user.email)

    async def test_old_token_rejected_after_password_change(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_password_changed_confirmation,
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )
        headers = await make_auth_header(test_db, user)

        await client.put(
            "/users/me/password",
            json={
                "old_password": OLD_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )

        response = await client.get(
            "/users/me",
            headers=headers,
        )

        assert response.status_code == 401

    async def test_returns_400_for_null_password_hash(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        response = await client.put(
            "/users/me/password",
            json={
                "old_password": "anything",
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )

        assert response.status_code == 400


class TestRequestEmailChange:
    async def test_returns_200_with_detail(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_email_change_verification,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 200
        assert "detail" in response.json()

    async def test_pending_email_stored_in_session(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_email_change_verification,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.pending_new_email == "new_email@gmail.com"
        assert session.email_change_code_hash is not None
        assert session.email_change_code_expires_at is not None

    async def test_current_email_not_changed(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_email_change_verification,
    ):
        user = await make_member(
            test_db,
            email="original@gmail.com",
        )
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )

        await test_db.refresh(user)

        assert user.email == "original@gmail.com"

    async def test_verification_email_sent_to_new_address(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        mock_send_email_change_verification,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )

        await asyncio.sleep(0)

        mock_send_email_change_verification.assert_called_once()
        assert (
            mock_send_email_change_verification.call_args.args[0]
            == "new_email@gmail.com"
        )

    async def test_returns_401_for_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
        )

        assert response.status_code == 401

    async def test_returns_422_for_invalid_email_format(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email",
            json={"new_email": "not_an_email"},
            headers=headers,
        )

        assert response.status_code == 422


class TestConfirmEmailChange:
    async def _setup_pending_change(
        self,
        test_db: AsyncSession,
        user: User,
        new_email: str = "new_email@gmail.com",
        expired: bool = False,
    ) -> str:
        raw_email_change_code, hashed_email_change_code = generate_email_change_code()

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        session.pending_new_email = new_email
        session.email_change_code_hash = hashed_email_change_code
        session.email_change_code_expires_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
            if expired
            else datetime.now(timezone.utc)
            + timedelta(minutes=settings.EMAIL_CHANGE_CODE_EXPIRES_MINUTES)
        )

        await test_db.commit()

        return raw_email_change_code

    async def test_email_updated_successfully(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        raw_code = await self._setup_pending_change(test_db, user)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email/confirm",
            json={"code": raw_code},
            headers=headers,
        )

        await test_db.refresh(user)

        assert response.status_code == 200
        assert "detail" in response.json()
        assert user.email == "new_email@gmail.com"

    async def test_user_logged_out_after_confirmation(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(
            test_db,
            password=OLD_PASSWORD,
        )
        raw_code = await self._setup_pending_change(test_db, user)

        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email/confirm",
            json={"code": raw_code},
            headers=headers,
        )

        response = await client.get(
            "/users/me",
            headers=headers,
        )

        assert response.status_code == 401

    async def test_returns_400_for_wrong_code(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        await self._setup_pending_change(test_db, user)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email/confirm",
            json={"code": "000000"},
            headers=headers,
        )

        assert response.status_code == 400

    async def test_returns_400_for_expired_code(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        raw_code = await self._setup_pending_change(test_db, user, expired=True)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email/confirm",
            json={"code": raw_code},
            headers=headers,
        )

        assert response.status_code == 400

    async def test_returns_400_when_no_pending_change(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/users/me/email/confirm",
            json={"code": "123456"},
            headers=headers,
        )

        assert response.status_code == 400

    async def test_email_not_changed_on_wrong_code(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(
            test_db,
            email="original@gmail.com",
        )
        await self._setup_pending_change(test_db, user)
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email/confirm",
            json={"code": "000000"},
            headers=headers,
        )

        await test_db.refresh(user)

        assert user.email == "original@gmail.com"

    async def test_returns_401_for_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/users/me/email/confirm",
            json={"code": "123456"},
        )

        assert response.status_code == 401

    async def test_session_fields_cleared_after_success(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        raw_code = await self._setup_pending_change(test_db, user)
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/users/me/email/confirm",
            json={"code": raw_code},
            headers=headers,
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.pending_new_email is None
        assert session.email_change_code_hash is None
        assert session.email_change_code_expires_at is None
