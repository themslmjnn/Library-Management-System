import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from tests.conftest import make_auth_header
from tests.constants import NEW_PASSWORD
from tests.factories import make_library_admin, make_member, make_system_admin
from user.repository import UserRepositoryBase
from user.schemas import CreateUserAdmin


class TestGetUsersAdmin:
    async def test_returns_paginated_users(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        await make_member(test_db)
        await make_member(test_db)

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            "/users",
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        assert data["total"] >= 2

    async def test_requires_system_admin_role(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        headers = await make_auth_header(test_db, library_admin)
        response = await client.get(
            "/users",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.get("/users")

        assert response.status_code == 401

    async def test_pagination_works(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        for _ in range(5):
            await make_member(test_db)

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            "/users?skip=0&limit=2",
            headers=headers,
        )

        data = response.json()

        assert len(data["items"]) == 2
        assert data["has_more"] is True

    async def test_filtering_works(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        for _ in range(5):
            await make_member(test_db)

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            "/users?sort_by=created_at&order=desc&skip=0&limit=20&role=member",
            headers=headers,
        )

        data = response.json()

        assert all(user["role"] == UserRole.member for user in data["items"])
        assert data["total"] >= 5

    async def test_does_not_show_other_system_admins(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        await make_system_admin(test_db)
        await make_library_admin(test_db)

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            "/users",
            headers=headers,
        )

        data = response.json()
        roles = [user["role"] for user in data["items"]]
        ids = [user["id"] for user in data["items"]]
        assert response.status_code == 200
        assert UserRole.library_admin in roles
        assert UserRole.system_admin not in roles
        assert system_admin.id not in ids


class TestGetUserByIdAdmin:
    async def test_returns_user_detail(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(
            f"/users/{user.id}",
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["role"] == UserRole.member

    async def test_returns_404_for_unknown_id(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999
        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(
            f"/users/{non_existant_id}",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_unauthenticated_request_returns_401(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999
        response = await client.get(f"/users/{non_existant_id}")

        assert response.status_code == 401

    async def test_returns_403_for_non_admin(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.get(f"/users/{user.id}", headers=headers)

        assert response.status_code == 403


class TestDeactivateUserAdmin:
    async def test_deactivates_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        await test_db.refresh(user)

        assert response.status_code == 204
        assert user.is_active is False

    async def test_returns_409_if_already_inactive(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db, is_active=False)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        assert response.status_code == 409

    async def test_receptionist_cannot_deactivate(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_invalidates_session(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)
        user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)
        session = user_session.session
        original_access_token_version = session.access_token_version

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        await test_db.refresh(user)
        user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)
        session = user_session.session

        assert response.status_code == 204
        assert user.is_active is False
        assert session.access_token_version == original_access_token_version + 1
        assert session.refresh_token_family is None
        assert session.refresh_token_hash is None
        assert session.refresh_token_expires_at is None


class TestActivateUserAdmin:
    async def test_activate_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=False,
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/activate",
            headers=headers,
        )

        await test_db.refresh(user)

        assert response.status_code == 204
        assert user.is_active is True

    async def test_returns_409_if_already_active(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(
            test_db,
            is_active=True,
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/activate",
            headers=headers,
        )

        assert response.status_code == 409

    async def test_receptionist_cannot_activate(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/users/{user.id}/activate",
            headers=headers,
        )

        assert response.status_code == 403


class TestCreateAccountAdmin:
    async def test_creates_user_with_invite_token(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        headers = await make_auth_header(test_db, system_admin)
        valid_create_user_request_admin.role = UserRole.library_admin

        response = await client.post(
            "/users",
            json=valid_create_user_request_admin.model_dump(mode="json"),
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 201
        assert data["id"] is not None
        assert data["role"] == "library_admin"
        assert data["is_active"] is False

    async def test_rejects_system_admin_role(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
    ):
        headers = await make_auth_header(test_db, system_admin)
        valid_create_user_request_admin.role = UserRole.system_admin

        response = await client.post(
            "/users",
            json=valid_create_user_request_admin.model_dump(mode="json"),
            headers=headers,
        )

        assert response.status_code == 403

    @pytest.mark.parametrize(
        ("existing_user_data", "request_override"),
        [
            (
                {"email": "taken@gmail.com"},
                {"email": "taken@gmail.com"},
            ),
            (
                {"username": "taken_username"},
                {"username": "taken_username"},
            ),
            (
                {"phone_number": "+992 000 000 000"},
                {"phone_number": "+992 000 000 000"},
            ),
        ],
    )
    async def test_reject_duplicate_fields(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        valid_create_user_request_admin: CreateUserAdmin,
        existing_user_data: dict,
        request_override: dict,
    ):
        await make_member(
            test_db,
            **existing_user_data,
        )

        for field, value in request_override.items():
            setattr(valid_create_user_request_admin, field, value)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.post(
            "/users",
            json=valid_create_user_request_admin.model_dump(mode="json"),
            headers=headers,
        )

        assert response.status_code == 409

    async def test_returns_403_for_non_admin(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        headers = await make_auth_header(test_db, library_admin)

        response = await client.post(
            "/users",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_rejects_invalid_input(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "first_name": "Co",
            "last_name": "Ca",
            "email": "duplicate@gmailcom",
            "phone_number": "+15550008888",
            "date_of_birth": "1990-01-01",
            "role": "member",
        }

        response = await client.post(
            "/users",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 422


class TestUpdateUserAdmin:
    async def test_updates_user_successfully(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)

        update_request = {
            "username": "new_test_username",
        }

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 200

    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999

        update_request = {
            "username": "new_test_username",
        }

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{non_existant_id}",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 404


class TestUpdateUserPasswordAdmin:
    async def test_successfully_updates_password(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)

        update_request = {
            "new_password": NEW_PASSWORD,
        }

        headers = await make_auth_header(test_db, system_admin)

        response = await client.put(
            f"/users/{user.id}/password",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 204

    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999

        update_request = {
            "new_password": NEW_PASSWORD,
        }

        headers = await make_auth_header(test_db, system_admin)

        response = await client.put(
            f"/users/{non_existant_id}/password",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 404

    async def test_returns_403_for_non_admin(
        self, test_db: AsyncSession, client: AsyncClient, library_admin
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.put(
            f"/users/{user.id}/password",
            json={"new_password": NEW_PASSWORD},
            headers=headers,
        )

        assert response.status_code == 403
