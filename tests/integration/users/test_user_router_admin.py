import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailType
from src.email.repository import PendingEmailRepository
from src.users.models import User, UserRole
from src.users.repository import UserRepositoryBase
from src.users.schemas import CreateUserAdmin
from tests.conftest import make_auth_header
from tests.factories import make_library_admin, make_member, make_system_admin


class TestCreateAccount:
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
        user = await UserRepositoryBase.get_user_by_id(
            test_db, data["id"], load_activation=True
        )
        user_activation = user.activation

        pending_email = await PendingEmailRepository.get_pending_email_by_triggered_by(
            test_db, system_admin.id
        )

        email = pending_email[0]

        assert response.status_code == 201
        assert len(pending_email) == 1
        assert data["id"] is not None
        assert data["role"] == "library_admin"
        assert data["is_active"] is False
        assert user_activation.invite_token_hash is not None
        assert user_activation.invite_token_expires_at is not None
        assert user_activation.invite_token_expires_at > datetime.now(timezone.utc)
        assert user_activation.user_id == data["id"]
        assert email.email_type == EmailType.invite

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
        assert response.json()["detail"] == "Cannot create system admin through the API"

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
        await make_member(test_db, **existing_user_data)

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

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        response = await client.post("/users")

        assert response.status_code == 401

    async def test_rejects_invalid_names(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)

        payload = {
            "first_name": "Name123",
            "last_name": "Surname123",
            "email": "duplicate@gmail.com",
            "phone_number": "+1 111 111 111",
            "date_of_birth": "1990-01-01",
            "role": "member",
        }

        response = await client.post(
            "/users",
            json=payload,
            headers=headers,
        )

        errors = response.json()["detail"]
        error_fields = [error["loc"][-1] for error in errors]

        assert response.status_code == 422
        assert "first_name" in error_fields
        assert "last_name" in error_fields

    async def test_rejects_invalid_phone_number(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)

        payload = {
            "first_name": "Name",
            "last_name": "Surname",
            "email": "duplicate@gmail.com",
            "phone_number": "1 11a 1d1",
            "date_of_birth": "1990-01-01",
            "role": "member",
        }

        response = await client.post(
            "/users",
            json=payload,
            headers=headers,
        )

        errors = response.json()["detail"]
        error_fields = [error["loc"][-1] for error in errors]

        assert response.status_code == 422
        assert "phone_number" in error_fields

    async def test_rejects_invalid_date_of_birth(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)

        payload = {
            "first_name": "Name",
            "last_name": "Surname",
            "email": "duplicate@gmail.com",
            "phone_number": "+1 111 111 111",
            "date_of_birth": "2015-01-01",
            "role": "member",
        }

        response = await client.post(
            "/users",
            json=payload,
            headers=headers,
        )

        errors = response.json()["detail"]
        error_fields = [error["loc"][-1] for error in errors]

        assert response.status_code == 422
        assert "date_of_birth" in error_fields


class TestGetUsers:
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
        assert data["total"] == 2

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
            "/users?sort_by=created_at&order=desc&skip=0&limit=10&role=member",
            headers=headers,
        )

        data = response.json()

        assert all(user["role"] == UserRole.member for user in data["items"])
        assert data["total"] == 5

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


class TestGetUserByID:
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
        assert data["username"] == user.username
        assert data["email"] == user.email
        assert data["phone_number"] == user.phone_number
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

        response = await client.get(
            f"/users/{user.id}",
            headers=headers,
        )

        assert response.status_code == 403


class TestDeactivateUser:
    async def test_deactivates_user(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_account_deactivation_email,
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
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_account_deactivation_email,
    ):
        user = await make_member(test_db, is_active=False)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        assert response.status_code == 409

    async def test_non_system_admin_cannot_deactivate(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        receptionist: User,
        mock_send_account_deactivation_email,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_invalidates_session(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_account_deactivation_email,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        original_access_token_version = 1

        response = await client.patch(
            f"/users/{user.id}/deactivate",
            headers=headers,
        )

        await test_db.refresh(user)
        user_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_session.session

        assert response.status_code == 204
        assert user.is_active is False
        assert session.access_token_version == original_access_token_version + 1
        assert session.refresh_token_family is None
        assert session.refresh_token_hash is None
        assert session.refresh_token_expires_at is None


class TestActivateUser:
    async def test_activate_user(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_account_activation_email,
    ):
        user = await make_member(test_db, is_active=False)
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
        user = await make_member(test_db, is_active=True)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/activate",
            headers=headers,
        )

        assert response.status_code == 409

    async def test_non_system_admin_cannot_activate(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/users/{user.id}/activate",
            headers=headers,
        )

        assert response.status_code == 403


class TestUpdateUserAdmin:
    async def test_updates_user_successfully(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)

        update_request = {"username": "new_test_username"}

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}",
            json=update_request,
            headers=headers,
        )

        data = response.json()

        assert response.status_code == 200
        assert data["username"] == "new_test_username"

    async def test_does_not_update_unknown_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999

        update_request = {"username": "new_test_username"}

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{non_existant_id}",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 404

    async def test_unauthenticated_request_returns_401(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)
        non_existant_id = user.id + 9999999

        update_request = {"username": "new_test_username"}

        response = await client.patch(
            f"/users/{non_existant_id}",
            json=update_request,
        )

        assert response.status_code == 401

    async def test_returns_403_for_non_admin(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        update_request = {"username": "new_test_username"}

        response = await client.patch(
            f"/users/{user.id}",
            json=update_request,
            headers=headers,
        )

        assert response.status_code == 403


class TestUpdateUserEmailAdmin:
    async def test_system_admin_can_update_email(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_admin_email_override_notification,
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 204

        await test_db.refresh(user)

        assert user.email == "updated_email@gmail.com"

    async def test_returns_404_for_unknown_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existent_id = user.id + 999999

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{non_existent_id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_returns_409_for_duplicate_email(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        await make_member(test_db, email="taken@gmail.com")
        user = await make_member(test_db)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "taken@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 409

    async def test_returns_403_for_library_admin(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 403

    async def test_returns_403_for_receptionist(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 403

    async def test_returns_401_for_unauthenticated(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)

        response = await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
        )

        assert response.status_code == 401

    async def test_returns_404_for_system_admin_target(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User, mocker
    ):
        other_system_admin = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/users/{other_system_admin.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_session_invalidated_after_email_update(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_admin_email_override_notification,
    ):
        user = await make_member(test_db)
        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        original_version = user_with_session.session.access_token_version

        headers = await make_auth_header(test_db, system_admin)

        await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.access_token_version == original_version + 1
        assert session.refresh_token_hash is None
        assert session.refresh_token_family is None
        assert session.refresh_token_expires_at is None

    async def test_notification_sent_to_old_email(
        self,
        test_db: AsyncSession,
        client: AsyncClient,
        system_admin: User,
        mock_send_admin_email_override_notification,
    ):
        user = await make_member(
            test_db,
            email="old_email@gmail.com",
        )

        headers = await make_auth_header(test_db, system_admin)

        await client.patch(
            f"/users/{user.id}/email",
            json={"new_email": "updated_email@gmail.com"},
            headers=headers,
        )

        await asyncio.sleep(0)

        mock_send_admin_email_override_notification.assert_called_once_with(
            "old_email@gmail.com"
        )


class TestCreateResetPasswordRequestAdmin:
    async def test_system_admin_can_create_request(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        assert response.status_code == 204

    async def test_library_admin_can_create_request(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        assert response.status_code == 204

    async def test_receptionist_cannot_create_request(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, receptionist)

        response = await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_member_cannot_create_request(
        self, test_db: AsyncSession, client: AsyncClient, member: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, member)

        response = await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        assert response.status_code == 403

    async def test_returns_401_for_unauthenticated(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        user = await make_member(test_db)

        response = await client.post(f"/users/{user.id}/password")

        assert response.status_code == 401

    async def test_returns_404_for_unknown_user(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        non_existent_id = user.id + 999999
        headers = await make_auth_header(test_db, system_admin)

        response = await client.post(
            f"/users/{non_existent_id}/password",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_library_admin_cannot_reset_system_admin_password(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        system_admin = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.post(
            f"/users/{system_admin.id}/password",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_library_admin_cannot_reset_other_library_admin_password(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        other_library_admin = await make_library_admin(test_db)
        headers = await make_auth_header(test_db, library_admin)

        response = await client.post(
            f"/users/{other_library_admin.id}/password",
            headers=headers,
        )

        assert response.status_code == 404

    async def test_pending_email_created_after_successful_request(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        pending_emails = await PendingEmailRepository.get_pending_email_by_triggered_by(
            test_db, system_admin.id
        )

        assert len(pending_emails) == 1
        assert pending_emails[0].email_type == EmailType.password_reset_admin
        assert pending_emails[0].recipient_user_id == user.id

    async def test_reset_token_written_to_session(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, system_admin)

        await client.post(
            f"/users/{user.id}/password",
            headers=headers,
        )

        user_with_session = await UserRepositoryBase.get_user_by_id(
            test_db, user.id, load_session=True
        )
        session = user_with_session.session

        assert session.reset_password_token_hash is not None
        assert session.reset_password_token_expires_at is not None
