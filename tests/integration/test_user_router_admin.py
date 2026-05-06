from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from tests.conftest import make_auth_header
from tests.factories import make_member


class TestGetUsersAdmin:
    async def test_returns_paginated_users(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        await make_member(test_db)
        await make_member(test_db)

        headers = make_auth_header(system_admin)
        response = await client.get("/users", headers=headers)

        assert response.status_code == 200

        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        assert data["total"] >= 2


    async def test_requires_system_admin_role(self, client: AsyncClient, library_admin: User):
        headers = make_auth_header(library_admin)
        response = await client.get("/users", headers=headers)

        assert response.status_code == 403


    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users")

        assert response.status_code == 401


    async def test_pagination_works(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        for _ in range(5):
            await make_member(test_db)

        headers = make_auth_header(system_admin)
        response = await client.get("/users?skip=0&limit=2", headers=headers)

        data = response.json()

        assert len(data["items"]) == 2
        assert data["has_more"] is True

    
    async def test_filtering_works(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        for _ in range(5):
            await make_member(test_db)

        headers = make_auth_header(system_admin)
        response = await client.get("/users?sort_by=created_at&order=desc&skip=0&limit=20&role=member", headers=headers)

        data = response.json()

        assert all(user["role"] == UserRole.member for user in data["items"])


class TestGetUserByIdAdmin:
    async def test_returns_user_detail(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.get(f"/users/{user.id}", headers=headers)

        data = response.json()

        assert response.status_code == 200
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["role"] == UserRole.member


    async def test_returns_404_for_unknown_id(self, client: AsyncClient, system_admin: User):
        headers = make_auth_header(system_admin)
        response = await client.get("/users/999999", headers=headers)

        assert response.status_code == 404


    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users/999999")

        assert response.status_code == 401


    async def test_returns_403_for_non_admin(self, test_db: AsyncSession, client: AsyncClient, library_admin: User):
        user = await make_member(test_db)
        headers = make_auth_header(library_admin)

        response = await client.get(f"/users/{user.id}", headers=headers)

        assert response.status_code == 403


class TestDeactivateUserAdmin:
    async def test_deactivates_user(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 204

        await test_db.refresh(user)

        assert user.is_active is False


    async def test_returns_409_if_already_inactive(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db, is_active=False)
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 409


    async def test_receptionist_cannot_deactivate(self, test_db: AsyncSession, client: AsyncClient, receptionist: User):
        user = await make_member(test_db)
        headers = make_auth_header(receptionist)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 403


class TestActivateUserAdmin:
    async def test_activate_user(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(
            test_db,
            is_active=False,
        )
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/activate", headers=headers)

        assert response.status_code == 204

        await test_db.refresh(user)

        assert user.is_active is True


    async def test_returns_409_if_already_active(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db, is_active=True)
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/activate", headers=headers)

        assert response.status_code == 409


    async def test_receptionist_cannot_activate(self, test_db: AsyncSession, client: AsyncClient, receptionist: User):
        user = await make_member(test_db)
        headers = make_auth_header(receptionist)

        response = await client.put(f"/users/{user.id}/activate", headers=headers)

        assert response.status_code == 403


class TestCreateAccountAdmin:
    async def test_creates_user_with_invite_token(self, client: AsyncClient, system_admin: User):
        headers = make_auth_header(system_admin)
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@gmail.com",
            "phone_number": "+15550001234",
            "date_of_birth": "1990-05-15",
            "role": "library_admin",
        }

        response = await client.post("/users", json=payload, headers=headers)

        assert response.status_code == 201

        data = response.json()

        assert data["role"] == "library_admin"
        assert data["is_active"] is False


    async def test_rejects_system_admin_role(self, client: AsyncClient, system_admin: User):
        headers = make_auth_header(system_admin)
        payload = {
            "first_name": "Evil",
            "last_name": "Actor",
            "email": "evil@gmail.com",
            "phone_number": "+15550009999",
            "date_of_birth": "1990-01-01",
            "role": "system_admin",
        }

        response = await client.post("/users", json=payload, headers=headers)

        assert response.status_code == 403


    async def test_rejects_duplicate_email(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        await make_member(
            test_db, 
            email="duplicate@gmail.com",
        )
        headers = make_auth_header(system_admin)
        payload = {
            "first_name": "Copy",
            "last_name": "Cat",
            "email": "duplicate@gmail.com",
            "phone_number": "+15550008888",
            "date_of_birth": "1990-01-01",
            "role": "member",
        }

        response = await client.post("/users", json=payload, headers=headers)

        assert response.status_code == 409


    async def test_returns_403_for_non_admin(self, client: AsyncClient, library_admin: User):
        headers = make_auth_header(library_admin)

        response = await client.post("/users", headers=headers)

        assert response.status_code == 403


    async def test_rejects_invalid_input(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        await make_member(test_db)
        headers = make_auth_header(system_admin)
        payload = {
            "first_name": "Co",
            "last_name": "Ca",
            "email": "duplicate@gmailcom",
            "phone_number": "+15550008888",
            "date_of_birth": "1990-01-01",
            "role": "member",
        }

        response = await client.post("/users", json=payload, headers=headers)

        assert response.status_code == 422


class TestUpdateUserAdmin:
    async def test_updates_user_successfully(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db)

        update_request = {
            "username": "new_test_username",
        }

        headers = make_auth_header(system_admin)

        response = await client.patch(f"/users/{user.id}", json=update_request, headers=headers)

        assert response.status_code == 200


    async def test_does_not_update_unknown_user(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        await make_member(test_db)

        update_request = {
            "username": "new_test_username",
        }

        headers = make_auth_header(system_admin)

        response = await client.patch("/users/99999999", json=update_request, headers=headers)

        assert response.status_code == 404

    
    async def test_does_not_upgrade_to_system_admin(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db)

        update_request = {
            "role": "system_admin",
        }

        headers = make_auth_header(system_admin)

        response = await client.patch(f"/users/{user.id}", json=update_request, headers=headers)

        assert response.status_code == 403


class TestUpdatePasswordAdmin:
    async def test_successfully_updates_password(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        user = await make_member(test_db)

        update_request = {
            "new_password": "NewPassword123!",
        }

        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/password", json=update_request, headers=headers)

        assert response.status_code == 204

    
    async def test_does_not_update_unknown_user(self, test_db: AsyncSession, client: AsyncClient, system_admin: User):
        await make_member(test_db)

        update_request = {
            "new_password": "NewPassword123!",
        }

        headers = make_auth_header(system_admin)

        response = await client.put("/users/999999/password", json=update_request, headers=headers)

        assert response.status_code == 404


    async def test_returns_403_for_non_admin(self, test_db: AsyncSession, client: AsyncClient, library_admin):
        user = await make_member(test_db)
        headers = make_auth_header(library_admin)

        response = await client.put(
            f"/users/{user.id}/password",
            json={"new_password": "NewPassword123!"},
            headers=headers,
        )

        assert response.status_code == 403