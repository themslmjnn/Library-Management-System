from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import UserRole
from tests.conftest import make_auth_header
from tests.constants import (
    CORRECT_PASSWORD,
    DEFAULT_PASSWORD,
    NEW_PASSWORD,
    WRONG_PASSWORD,
)
from tests.factories import (
    make_invited_user,
    make_member,
    make_user_with_activation_code,
)
from user.repository import UserRepositoryBase


class TestLogin:
    async def test_login_returns_access_token(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        await make_member(
            test_db,
            email="login@gmail.com",
            password=DEFAULT_PASSWORD,
        )

        response = await client.post(
            "/auth/login",
            data={
                "username": "login@gmail.com",
                "password": DEFAULT_PASSWORD,
            },
        )

        data = response.json()

        assert response.status_code == 200
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_sets_refresh_cookie(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        await make_member(
            test_db,
            email="cookie@gmail.com",
            password=DEFAULT_PASSWORD,
        )

        response = await client.post(
            "/auth/login",
            data={
                "username": "cookie@gmail.com",
                "password": DEFAULT_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "refresh_token" in response.cookies

    async def test_login_fails_wrong_password(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        await make_member(
            test_db,
            email="wrongpass@gmail.com",
            password=DEFAULT_PASSWORD,
        )

        response = await client.post(
            "/auth/login",
            data={
                "username": "wrongpass@gmail.com",
                "password": WRONG_PASSWORD,
            },
        )

        assert response.status_code == 401

    async def test_login_fails_unknown_user(self, client: AsyncClient):
        response = await client.post(
            "/auth/login",
            data={
                "username": "ghost@gmail.com",
                "password": CORRECT_PASSWORD,
            },
        )

        assert response.status_code == 401

    async def test_login_fails_inactive_account(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        await make_member(
            test_db,
            email="inactive@gmail.com",
            password=CORRECT_PASSWORD,
            is_active=False,
        )

        response = await client.post(
            "/auth/login",
            data={
                "username": "inactive@gmail.com",
                "password": CORRECT_PASSWORD,
            },
        )

        assert response.status_code == 403

    async def test_login_does_not_expose_whether_email_exists(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        await make_member(
            test_db,
            email="exists@gmail.com",
            password=DEFAULT_PASSWORD,
        )

        r1 = await client.post(
            "/auth/login",
            data={
                "username": "exists@gmail.com",
                "password": WRONG_PASSWORD,
            },
        )

        r2 = await client.post(
            "/auth/login",
            data={
                "username": "notexists@gmail.com",
                "password": WRONG_PASSWORD,
            },
        )

        assert r1.status_code == r2.status_code == 401
        assert r1.json()["detail"] == r2.json()["detail"]


class TestLogout:
    async def test_logout_returns_204(self, client: AsyncClient, test_db: AsyncSession):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/auth/logout",
            headers=headers,
        )

        assert response.status_code == 204

    async def test_logout_clears_refresh_cookie(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        await client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": CORRECT_PASSWORD,
            },
        )

        headers = await make_auth_header(test_db, user)

        response = await client.post(
            "/auth/logout",
            headers=headers,
        )

        cookie = client.cookies.get("refresh_token")

        assert not cookie
        assert response.status_code == 204

    async def test_logout_requires_authentication(self, client: AsyncClient):
        response = await client.post("/auth/logout")

        assert response.status_code == 401

    async def test_token_rejected_after_logout(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user = await make_member(test_db)
        headers = await make_auth_header(test_db, user)

        await client.post(
            "/auth/logout",
            headers=headers,
        )

        await test_db.refresh(user)

        response = await client.get(
            "/users/me",
            headers=headers,
        )

        assert response.status_code == 401


class TestActivateWithToken:
    async def test_activation_succeeds(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, raw_token = await make_invited_user(
            test_db,
            role=UserRole.member,
        )

        response = await client.post(
            "/auth/activate_with_token",
            json={
                "email": user.email,
                "invite_token": raw_token,
                "password": NEW_PASSWORD,
            },
        )

        assert response.status_code == 204

        await test_db.refresh(user)

        assert user.is_active is True

    async def test_activation_fails_wrong_token(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, _ = await make_invited_user(test_db)

        response = await client.post(
            "/auth/activate_with_token",
            json={
                "email": user.email,
                "invite_token": "completelyWrongToken",
                "password": NEW_PASSWORD,
            },
        )

        assert response.status_code == 400

    async def test_activation_fails_bad_password(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, raw_token = await make_invited_user(test_db)

        response = await client.post(
            "/auth/activate_with_token",
            json={
                "email": user.email,
                "invite_token": raw_token,
                "password": "weak",
            },
        )

        assert response.status_code == 422

    async def test_token_cannot_be_used_twice(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, raw_token = await make_invited_user(test_db)

        payload = {
            "email": user.email,
            "invite_token": raw_token,
            "password": NEW_PASSWORD,
        }

        r1 = await client.post(
            "/auth/activate_with_token",
            json=payload,
        )
        r2 = await client.post(
            "/auth/activate_with_token",
            json=payload,
        )

        assert r1.status_code == 204
        assert r2.status_code == 400

        await test_db.refresh(user)
        user_activation = await UserRepositoryBase.get_user_with_activation(
            test_db, user.id
        )

        assert user.is_active is True
        assert user_activation.activation.invite_token_hash is None


class TestActivateWithCode:
    async def test_activation_succeeds(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, raw_code = await make_user_with_activation_code(test_db)

        response = await client.post(
            "/auth/activate_with_code",
            json={
                "email": user.email,
                "code": raw_code,
            },
        )

        assert response.status_code == 204

        await test_db.refresh(user)

        assert user.is_active is True

    async def test_activation_fails_wrong_code(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, _ = await make_user_with_activation_code(test_db)

        response = await client.post(
            "/auth/activate_with_code",
            json={
                "email": user.email,
                "code": "000000ff",
            },
        )

        assert response.status_code == 400

    async def test_code_cannot_be_used_twice(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user, raw_code = await make_user_with_activation_code(test_db)

        payload = {
            "email": user.email,
            "code": raw_code,
        }

        r1 = await client.post(
            "/auth/activate_with_code",
            json=payload,
        )
        r2 = await client.post(
            "/auth/activate_with_code",
            json=payload,
        )

        assert r1.status_code == 204
        assert r2.status_code == 400

    async def test_activation_fails_unknown_email(self, client, test_db):
        response = await client.post(
            "/auth/activate_with_code",
            json={
                "email": "nobody@gmail.com",
                "code": "anycode",
            },
        )

        assert response.status_code == 400


class TestRefreshToken:
    async def test_refresh_returns_new_access_token(self, client, test_db):
        user = await make_member(test_db, password=DEFAULT_PASSWORD)

        await client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": DEFAULT_PASSWORD,
            },
        )

        response = await client.post("/auth/refresh_token")

        data = response.json()

        assert response.status_code == 200
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_fails_without_cookie(self, client: AsyncClient):
        response = await client.post("/auth/refresh_token")

        assert response.status_code == 401

    async def test_refresh_rotates_cookie(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        await client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": CORRECT_PASSWORD,
            },
        )

        old_cookie = client.cookies.get("refresh_token")
        await client.post("/auth/refresh_token")
        new_cookie = client.cookies.get("refresh_token")

        assert old_cookie != new_cookie

    async def test_reused_refresh_token_invalidates_all_sessions(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        user = await make_member(
            test_db,
            password=CORRECT_PASSWORD,
        )

        user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)

        original_version = user_session.session.access_token_version

        await client.post(
            "/auth/login",
            data={
                "username": user.email,
                "password": CORRECT_PASSWORD,
            },
        )

        old_cookie = client.cookies.get("refresh_token")
        await client.post("/auth/refresh_token")
        client.cookies.set(
            "refresh_token",
            old_cookie,
        )
        response = await client.post("/auth/refresh_token")

        assert response.status_code == 401

        user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)

        assert user_session.session.refresh_token_hash is None
        assert user_session.session.refresh_token_family is None
        assert user_session.session.refresh_token_expires_at is None
        assert user_session.session.access_token_version == original_version + 1
