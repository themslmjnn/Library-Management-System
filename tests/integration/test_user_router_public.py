from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_auth_header
from tests.factories import make_member


class TestGetMe:
    async def test_returns_user_detail(self, test_db: AsyncSession, client: AsyncClient):
        user = await make_member(
            test_db,
            email="test_email@gmail.com",
        )

        headers = make_auth_header(user)

        response = await client.get("/users/me", headers=headers)

        data = response.json()

        assert response.status_code == 200
        assert data["id"] == user.id
        assert data["email"] == "test_email@gmail.com"


    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users/me")

        assert response.status_code == 401

    
class TestCreateAccountPublic:
    async def test_creates_user(self, test_db: AsyncSession, client: AsyncClient):
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-05-15",
            "email": "jane@gmail.com",
            "phone_number": "+15550001234",
            "password": "Valid123!",
        }

        response = await client.post("/users/me", json=payload)

        assert response.status_code == 201

    
    async def test_rejects_duplicate_email(self, test_db: AsyncSession, client: AsyncClient):
        await make_member(
            test_db, 
            email="duplicate@gmail.com",
        )

        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-05-15",
            "email": "duplicate@gmail.com",
            "phone_number": "+15550001234",
            "password": "Valid123!",
        }

        response = await client.post("/users/me", json=payload)

        assert response.status_code == 409

    
    async def test_rejects_invalid_input(self, test_db: AsyncSession, client: AsyncClient):
        await make_member(test_db)
      
        payload = {
            "first_name": "Co",
            "last_name": "Ca",
            "email": "duplicate@gmailcom",
            "phone_number": "+15550008888",
            "date_of_birth": "1990-01-01",

        }

        response = await client.post("/users/me", json=payload)

        assert response.status_code == 422


class TestUpdateUserPublic:
    async def test_updates_me_successfully(self, test_db: AsyncSession, client: AsyncClient):
        user = await make_member(test_db)

        update_request = {
            "username": "new_test_username",
        }

        headers = make_auth_header(user)

        response = await client.patch("/users/me", json=update_request, headers=headers)

        assert response.status_code == 200


    async def test_reject_duplicate_email(self, test_db: AsyncSession, client: AsyncClient):
        await make_member(
            test_db,
            email="taken@gmail.com",
        )

        user_to_be_updated = await make_member(
            test_db,
            email="other@gmail.com",
        )

        update_request = {
            "email": "taken@gmail.com",
        }

        headers = make_auth_header(user_to_be_updated)

        response = await client.patch("/users/me", json=update_request, headers=headers)

        assert response.status_code == 409


class TestUpdatePasswordPublic:
    async def test_successfully_updates_password(self, test_db: AsyncSession, client: AsyncClient):
        user = await make_member(
            test_db,
            password="OldPassword123!",
        )

        update_request = {
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
        }

        headers = make_auth_header(user)

        response = await client.put("/users/me/password", json=update_request, headers=headers)

        assert response.status_code == 204


    async def test_reject_incorrect_old_password(self, test_db: AsyncSession, client: AsyncClient):
        user = await make_member(
            test_db,
            password="OldPassword123!",
        )

        update_request = {
            "old_password": "IncorrectOldPassword123!",
            "new_password": "NewPassword123!",
        }

        headers = make_auth_header(user)

        response = await client.put("/users/me/password", json=update_request, headers=headers)

        assert response.status_code == 400

    
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.put("/users/me/password")

        assert response.status_code == 401