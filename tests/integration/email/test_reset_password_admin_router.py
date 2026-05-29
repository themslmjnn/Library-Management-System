from unittest.mock import AsyncMock

from tests.conftest import make_auth_header
from tests.factories import (
    make_guest,
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
)

PASSWORD_RESET_PATH = "/users/{user_id}/password"


def url(user_id: int) -> str:
    return PASSWORD_RESET_PATH.format(user_id=user_id)


class TestSystemAdminAllowedTargets:
    async def test_can_reset_library_admin_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        target = await make_library_admin(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204

    async def test_can_reset_receptionist_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        target = await make_receptionist(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204

    async def test_can_reset_member_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        target = await make_member(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204

    async def test_can_reset_guest_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        target = await make_guest(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204


class TestSystemAdminDeniedTargets:
    async def test_cannot_reset_another_system_admin_password(
        self, client, test_db, mocker
    ):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        target = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 404

    async def test_cannot_reset_own_password_via_admin_endpoint(
        self, client, test_db, mocker
    ):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(admin.id), headers=headers)

        assert response.status_code == 404


class TestLibraryAdminAllowedTargets:
    async def test_can_reset_receptionist_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_library_admin(test_db)
        target = await make_receptionist(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204

    async def test_can_reset_member_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_library_admin(test_db)
        target = await make_member(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204

    async def test_can_reset_guest_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_library_admin(test_db)
        target = await make_guest(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 204


class TestLibraryAdminDeniedTargets:
    async def test_cannot_reset_system_admin_password(self, client, test_db, mocker):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        lib_admin = await make_library_admin(test_db)
        target = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, lib_admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 404

    async def test_cannot_reset_another_library_admin_password(
        self, client, test_db, mocker
    ):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        lib_admin = await make_library_admin(test_db)
        target = await make_library_admin(test_db)
        headers = await make_auth_header(test_db, lib_admin)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 404

    async def test_cannot_reset_own_password_via_admin_endpoint(
        self, client, test_db, mocker
    ):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        lib_admin = await make_library_admin(test_db)
        headers = await make_auth_header(test_db, lib_admin)

        response = await client.post(url(lib_admin.id), headers=headers)

        assert response.status_code == 404


class TestUnauthorizedRoles:
    async def test_receptionist_gets_403(self, client, test_db):
        actor = await make_receptionist(test_db)
        target = await make_member(test_db)
        headers = await make_auth_header(test_db, actor)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 403

    async def test_member_gets_403(self, client, test_db):
        actor = await make_member(test_db)
        target = await make_guest(test_db)
        headers = await make_auth_header(test_db, actor)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 403

    async def test_guest_gets_403(self, client, test_db):
        actor = await make_guest(test_db)
        target = await make_member(test_db)
        headers = await make_auth_header(test_db, actor)

        response = await client.post(url(target.id), headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_gets_401(self, client, test_db):
        target = await make_member(test_db)

        response = await client.post(url(target.id))

        assert response.status_code == 401

    async def test_nonexistent_target_returns_404_for_system_admin(
        self, client, test_db, mocker
    ):
        mocker.patch(
            "src.users.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
        admin = await make_system_admin(test_db)
        headers = await make_auth_header(test_db, admin)

        response = await client.post(url(99999), headers=headers)

        assert response.status_code == 404
