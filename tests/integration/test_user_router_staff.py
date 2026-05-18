from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User
from tests.conftest import make_auth_header
from tests.factories import make_member, make_system_admin
from user.schemas import CreateUserBase


class TestGetUsersStaff:
    async def test_returns_paginated_users(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        await make_member(test_db)
        await make_member(test_db)

        headers = await make_auth_header(test_db, library_admin)
        response = await client.get(
            "/users/staff",
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        assert data["total"] >= 2

    async def test_reject_other_roles_except_library_admin(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            "/users/staff",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_reject_other_roles_except_receptionist(
        self, test_db: AsyncSession, client: AsyncClient, member: User
    ):
        headers = await make_auth_header(test_db, member)
        response = await client.get(
            "/users/staff",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users/staff")

        assert response.status_code == 401

    async def test_pagination_works(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        for _ in range(5):
            await make_member(test_db)

        headers = await make_auth_header(test_db, library_admin)
        response = await client.get(
            "/users/staff?skip=0&limit=2",
            headers=headers,
        )

        data = response.json()

        assert len(data["items"]) == 2
        assert data["has_more"] is True


class TestGetUserByIDStaff:
    async def test_returns_user_detail(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.get(
            f"/users/{user.id}/staff",
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["role"] == "member"

    async def test_returns_404_for_fetching_higher_roles(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.get(
            f"/users/{user.id}/staff",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_returns_404_for_unknown_id(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        headers = await make_auth_header(test_db, library_admin)
        response = await client.get(
            f"/users/{non_existant_id}/staff",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_unauthenticated_request_returns_401(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 999999

        response = await client.get(f"/users/{non_existant_id}/staff")

        assert response.status_code == 401

    async def test_require_library_admin(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(
            f"/users/{user.id}/staff",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_require_receptionist(
        self, test_db: AsyncSession, client: AsyncClient, member: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        response = await client.get(
            f"/users/{user.id}/staff",
            headers=headers,
        )

        assert response.status_code == 403


class TestCreateAccountStaff:
    async def test_creates_user_with_invite_token(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        library_admin: User,
        valid_create_user_request_staff: CreateUserBase,
    ):
        headers = await make_auth_header(test_db, library_admin)

        response = await client.post(
            "/users/staff",
            json=valid_create_user_request_staff.model_dump(mode="json"),
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 201
        assert data["role"] == "guest"

    async def test_require_library_admin(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)

        response = await client.post(
            "/users/staff",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_require_receptionist(
        self, test_db: AsyncSession, client: AsyncClient, member: User
    ):
        headers = await make_auth_header(test_db, member)

        response = await client.post(
            "/users/staff",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_rejects_invalid_input(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)
        payload = {
            "first_name": "Co",
            "last_name": "Ca",
            "email": "duplicate@gmailcom",
            "phone_number": "+15550008888",
            "date_of_birth": "1990-01-01",
        }

        response = await client.post(
            "/users/staff",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 422
