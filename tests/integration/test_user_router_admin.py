import pytest
from httpx import AsyncClient

from src.user.models import UserRole
from tests.conftest import make_auth_header
from tests.factories import make_member, make_system_admin, make_user


class TestGetUsersAdmin:
    async def test_returns_paginated_users(self, client: AsyncClient, system_admin, test_db):
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


    async def test_requires_system_admin_role(self, client: AsyncClient, library_admin):
        headers = make_auth_header(library_admin)
        response = await client.get("/users", headers=headers)

        assert response.status_code == 403


    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users")
        assert response.status_code == 401


    async def test_pagination_works(self, client: AsyncClient, system_admin, test_db):
        for _ in range(5):
            await make_member(test_db)

        headers = make_auth_header(system_admin)
        response = await client.get("/users?skip=0&limit=2", headers=headers)

        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True


class TestGetUserByIdAdmin:
    async def test_returns_user_detail(self, client: AsyncClient, system_admin, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.get(f"/users/{user.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["role"] == UserRole.member

    async def test_returns_404_for_unknown_id(self, client: AsyncClient, system_admin):
        headers = make_auth_header(system_admin)
        response = await client.get("/users/99999", headers=headers)
        assert response.status_code == 404

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users/2")
        assert response.status_code == 401

    async def test_returns_403_for_non_admin(self, client: AsyncClient, library_admin, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(library_admin)

        response = await client.get(f"/users/{user.id}", headers=headers)

        assert response.status_code == 403


class TestDeactivateUserAdmin:
    async def test_deactivates_user(self, client: AsyncClient, system_admin, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 204
        await test_db.refresh(user)
        assert user.is_active is False

    async def test_returns_409_if_already_inactive(self, client: AsyncClient, system_admin, test_db):
        user = await make_member(test_db, is_active=False)
        headers = make_auth_header(system_admin)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 409

    async def test_receptionist_cannot_deactivate(self, client: AsyncClient, receptionist, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(receptionist)

        response = await client.put(f"/users/{user.id}/deactivate", headers=headers)

        assert response.status_code == 403


class TestCreateAccountAdmin:
    async def test_creates_user_with_invite_token(self, client: AsyncClient, system_admin):
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

    async def test_rejects_system_admin_role(self, client: AsyncClient, system_admin):
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

    async def test_rejects_duplicate_email(self, client: AsyncClient, system_admin, test_db):
        await make_member(test_db, email="duplicate@gmail.com")
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


    async def test_returns_403_for_non_admin(self, client: AsyncClient, library_admin):
        headers = make_auth_header(library_admin)

        response = await client.post("/users", headers=headers)

        assert response.status_code == 403