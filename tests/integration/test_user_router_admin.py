from src.user.models import UserRole
from tests.factories import make_user, make_member, make_system_admin
from tests.conftest import make_auth_header
import pytest
from httpx import AsyncClient

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