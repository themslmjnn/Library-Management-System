import asyncio

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.repository import UserRepositoryBase
from src.users.schemas import CreateUserPublic
from src.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.constants import CORRECT_PASSWORD, NEW_PASSWORD, OLD_PASSWORD
from tests.factories import make_member
from utils.response_messages import PublicMessages


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
        self, test_db: AsyncSession, client: AsyncClient, mock_send_already_registered_email
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
        self, test_db: AsyncSession, client: AsyncClient, mock_send_already_registered_email
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
        self, test_db: AsyncSession, client: AsyncClient
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
            "/users/me/password", json=update_request, headers=headers
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
 
class TestRequestEmailChange:
 
    async def test_returns_200_with_detail(
        self, test_db: AsyncSession, client: AsyncClient, mocker
    ):
        mocker.patch(
            "src.users.service.email_sender.send_email_change_verification",
            new_callable=AsyncMock,
        )
 
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
        self, test_db: AsyncSession, client: AsyncClient, mocker
    ):
        mocker.patch(
            "src.users.service.email_sender.send_email_change_verification",
            new_callable=AsyncMock,
        )
 
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)
 
        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )
 
        user_with_session = await UserRepositoryBase.get_user_by_id_with_session(
            test_db, user.id
        )
        session = user_with_session.session
 
        assert session.pending_new_email == "new_email@gmail.com"
        assert session.email_change_code_hash is not None
        assert session.email_change_code_expires_at is not None
 
    async def test_current_email_not_changed(
        self, test_db: AsyncSession, client: AsyncClient, mocker
    ):
        mocker.patch(
            "src.users.service.email_sender.send_email_change_verification",
            new_callable=AsyncMock,
        )
 
        user = await make_member(test_db, email="original@gmail.com")
        headers = await make_auth_header(test_db, user)
 
        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )
 
        await test_db.refresh(user)
 
        assert user.email == "original@gmail.com"
 
    async def test_verification_email_sent_to_new_address(
        self, test_db: AsyncSession, client: AsyncClient, mocker
    ):
        mock_send = mocker.patch(
            "src.users.service.email_sender.send_email_change_verification",
            new_callable=AsyncMock,
        )
 
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)
 
        await client.post(
            "/users/me/email",
            json={"new_email": "new_email@gmail.com"},
            headers=headers,
        )
 
        await asyncio.sleep(0)
 
        mock_send.assert_called_once()
        assert mock_send.call_args.args[0] == "new_email@gmail.com"
 
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
 
 