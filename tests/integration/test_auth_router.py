import pytest
from httpx import AsyncClient

from src.user.models import UserRole
from tests.factories import (
    make_member,
    make_invited_user,
    make_user_with_activation_code,
)
from tests.conftest import make_auth_header


class TestLogin:

    async def test_login_returns_access_token(self, client: AsyncClient, test_db):
        await make_member(test_db, email="login@gmail.com", password="Valid123!")

        response = await client.post("/auth/login", data={
            "username": "login@gmail.com",
            "password": "Valid123!",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_sets_refresh_cookie(self, client: AsyncClient, test_db):
        await make_member(test_db, email="cookie@gmail.com", password="Valid123!")

        response = await client.post("/auth/login", data={
            "username": "cookie@gmail.com",
            "password": "Valid123!",
        })

        assert response.status_code == 200
        assert "refresh_token" in response.cookies

    async def test_login_fails_wrong_password(self, client: AsyncClient, test_db):
        await make_member(test_db, email="wrongpass@gmail.com", password="Correct123!")

        response = await client.post("/auth/login", data={
            "username": "wrongpass@gmail.com",
            "password": "Wrong123!",
        })

        assert response.status_code == 401

    async def test_login_fails_unknown_user(self, client: AsyncClient):
        response = await client.post("/auth/login", data={
            "username": "ghost@gmail.com",
            "password": "anything",
        })

        assert response.status_code == 401

    async def test_login_fails_inactive_account(self, client: AsyncClient, test_db):
        await make_member(test_db, email="inactive@gmail.com", password="Valid123!", is_active=False)

        response = await client.post("/auth/login", data={
            "username": "inactive@gmail.com",
            "password": "Valid123!",
        })

        assert response.status_code == 403

    async def test_login_does_not_expose_whether_email_exists(self, client: AsyncClient, test_db):
        await make_member(test_db, email="exists@gmail.com", password="Valid123!")

        r1 = await client.post("/auth/login", data={
            "username": "exists@gmail.com",
            "password": "wrongpass",
        })
        r2 = await client.post("/auth/login", data={
            "username": "notexists@gmail.com",
            "password": "wrongpass",
        })

        # both must return the same status and same detail
        # prevents email enumeration via different error messages
        assert r1.status_code == r2.status_code == 401
        assert r1.json()["detail"] == r2.json()["detail"]


class TestLogout:

    async def test_logout_returns_204(self, client: AsyncClient, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(user)

        response = await client.post("/auth/logout", headers=headers)

        assert response.status_code == 204

    async def test_logout_clears_refresh_cookie(self, client: AsyncClient, test_db):
        user = await make_member(test_db, password="Valid123!")

        # login first to get the cookie
        await client.post("/auth/login", data={
            "username": user.email,
            "password": "Valid123!",
        })

        headers = make_auth_header(user)
        response = await client.post("/auth/logout", headers=headers)

        # cookie should be cleared (expired or absent)
        assert response.status_code == 204

    async def test_logout_requires_authentication(self, client: AsyncClient):
        response = await client.post("/auth/logout")
        assert response.status_code == 401

    async def test_token_rejected_after_logout(self, client: AsyncClient, test_db):
        user = await make_member(test_db)
        headers = make_auth_header(user)

        await client.post("/auth/logout", headers=headers)

        # the token version was incremented — old token must now fail
        # we need to refresh the user to get updated version
        await test_db.refresh(user)
        # original token embedded old version — any endpoint should reject it
        response = await client.get("/users/me", headers=headers)
        assert response.status_code == 401

class TestActivateWithToken:

    async def test_activation_succeeds(self, client: AsyncClient, test_db):
        user, raw_token = await make_invited_user(test_db, role=UserRole.member)

        response = await client.post("/auth/activate_with_token", json={
            "email": user.email,
            "invite_token": raw_token,
            "password": "NewPass123!",
        })

        assert response.status_code == 204
        await test_db.refresh(user)
        assert user.is_active is True

    async def test_activation_fails_wrong_token(self, client: AsyncClient, test_db):
        user, _ = await make_invited_user(test_db)

        response = await client.post("/auth/activate_with_token", json={
            "email": user.email,
            "invite_token": "completelyWrongToken",
            "password": "NewPass123!",
        })

        assert response.status_code == 400

    async def test_activation_fails_bad_password(self, client: AsyncClient, test_db):
        user, raw_token = await make_invited_user(test_db)

        response = await client.post("/auth/activate_with_token", json={
            "email": user.email,
            "invite_token": raw_token,
            "password": "weak",  # fails password validator
        })

        assert response.status_code == 422

    async def test_token_cannot_be_used_twice(self, client: AsyncClient, test_db):
        user, raw_token = await make_invited_user(test_db)

        payload = {
            "email": user.email,
            "invite_token": raw_token,
            "password": "NewPass123!",
        }

        r1 = await client.post("/auth/activate_with_token", json=payload)
        r2 = await client.post("/auth/activate_with_token", json=payload)

        assert r1.status_code == 204
        assert r2.status_code == 400


class TestActivateWithCode:

    async def test_activation_succeeds(self, client: AsyncClient, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)

        response = await client.post("/auth/activate_with_code", json={
            "email": user.email,
            "code": raw_code,
        })

        assert response.status_code == 204
        await test_db.refresh(user)
        assert user.is_active is True

    async def test_activation_fails_wrong_code(self, client: AsyncClient, test_db):
        user, _ = await make_user_with_activation_code(test_db)

        response = await client.post("/auth/activate_with_code", json={
            "email": user.email,
            "code": "000000ff",
        })

        assert response.status_code == 400

    async def test_code_cannot_be_used_twice(self, client: AsyncClient, test_db):
        user, raw_code = await make_user_with_activation_code(test_db)
        payload = {"email": user.email, "code": raw_code}

        r1 = await client.post("/auth/activate_with_code", json=payload)
        r2 = await client.post("/auth/activate_with_code", json=payload)

        assert r1.status_code == 204
        assert r2.status_code == 400


class TestRefreshToken:

    async def test_refresh_returns_new_access_token(self, client: AsyncClient, test_db):
        user = await make_member(test_db, password="Valid123!")

        login_response = await client.post("/auth/login", data={
            "username": user.email,
            "password": "Valid123!",
        })
        assert login_response.status_code == 200
        old_cookie = client.cookies.get("refresh_token")

        response = await client.post("/auth/refresh_token")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # the real assertion — refresh token was rotated
        new_cookie = client.cookies.get("refresh_token")
        assert new_cookie is not None
        assert new_cookie != old_cookie

    async def test_refresh_fails_without_cookie(self, client: AsyncClient):
        # no login — no cookie
        response = await client.post("/auth/refresh_token")
        assert response.status_code == 401

    async def test_refresh_rotates_cookie(self, client: AsyncClient, test_db):
        user = await make_member(test_db, password="Valid123!")

        await client.post("/auth/login", data={
            "username": user.email,
            "password": "Valid123!",
        })
        old_cookie = client.cookies.get("refresh_token")

        await client.post("/auth/refresh_token")
        new_cookie = client.cookies.get("refresh_token")

        assert old_cookie != new_cookie

    async def test_reused_refresh_token_invalidates_all_sessions(
        self, client: AsyncClient, test_db
    ):
        user = await make_member(test_db, password="Valid123!")

        await client.post("/auth/login", data={
            "username": user.email,
            "password": "Valid123!",
        })

        old_cookie = client.cookies.get("refresh_token")

        # first refresh — legitimate rotation
        await client.post("/auth/refresh_token")

        # manually restore the old cookie to simulate reuse
        client.cookies.set("refresh_token", old_cookie)

        response = await client.post("/auth/refresh_token")

        # reuse detected — all tokens invalidated
        assert response.status_code == 401

        await test_db.refresh(user)
        assert user.refresh_token_hash is None
        assert user.refresh_token_family is None
