class TestCreateResetPasswordRequestEndpoint:
 
    @pytest.mark.asyncio
    async def test_returns_204_for_known_email(self, client, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.modules.auth.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
 
        response = await client.post(
            RESET_REQUEST_PATH,
            json={"identifier": user.email},
        )
 
        assert response.status_code == 204
 
    @pytest.mark.asyncio
    async def test_returns_204_for_unknown_email(self, client):
        """
        Must return 204 even for unknown identifiers — no enumeration leakage.
        """
        response = await client.post(
            RESET_REQUEST_PATH,
            json={"identifier": "nobody@example.com"},
        )
 
        assert response.status_code == 204
 
    @pytest.mark.asyncio
    async def test_returns_204_for_username_identifier(self, client, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.modules.auth.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
 
        response = await client.post(
            RESET_REQUEST_PATH,
            json={"identifier": user.username},
        )
 
        assert response.status_code == 204
 
    @pytest.mark.asyncio
    async def test_returns_204_for_phone_number_identifier(self, client, test_db, mocker):
        user = await make_member(test_db, password=CORRECT_PASSWORD)
        mocker.patch(
            "src.modules.auth.service.send_reset_password_token",
            new_callable=AsyncMock,
        )
 
        response = await client.post(
            RESET_REQUEST_PATH,
            json={"identifier": user.phone_number},
        )
 
        assert response.status_code == 204
 
    @pytest.mark.asyncio
    async def test_rate_limited_after_threshold(self, client):
        for _ in range(5):
            await client.post(
                RESET_REQUEST_PATH,
                json={"identifier": "nobody@example.com"},
            )
 
        response = await client.post(
            RESET_REQUEST_PATH,
            json={"identifier": "nobody@example.com"},
        )
 
        assert response.status_code == 429
 
 
class TestResetPasswordEndpoint:
 
    @pytest.mark.asyncio
    async def test_valid_request_returns_204(self, client, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
 
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": user.email,
                "reset_token": raw_token,
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 204
 
    @pytest.mark.asyncio
    async def test_unknown_identifier_returns_401(self, client):
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": "nobody@example.com",
                "reset_token": FAKE_TOKEN,
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 401
 
    @pytest.mark.asyncio
    async def test_expired_token_returns_400(self, client, test_db):
        user, raw_token = await make_user_with_reset_token(test_db, expired=True)
 
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": user.email,
                "reset_token": raw_token,
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 400
 
    @pytest.mark.asyncio
    async def test_wrong_token_returns_400(self, client, test_db):
        user, _ = await make_user_with_reset_token(test_db)
 
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": user.email,
                "reset_token": "wrong_token",
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 400
 
    @pytest.mark.asyncio
    async def test_no_reset_token_requested_returns_400(self, client, test_db):
        """
        A user who never requested a reset has NULL expiry — must return 400,
        not 500.
        """
        user = await make_member(test_db, password=CORRECT_PASSWORD)
 
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": user.email,
                "reset_token": FAKE_TOKEN,
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 400
 
    @pytest.mark.asyncio
    async def test_token_reuse_returns_400(self, client, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
        payload = {
            "identifier": user.email,
            "reset_token": raw_token,
            "new_password": NEW_PASSWORD,
        }
 
        first = await client.post(RESET_PATH, json=payload)
        assert first.status_code == 204
 
        second = await client.post(RESET_PATH, json=payload)
        assert second.status_code == 400
 
    @pytest.mark.asyncio
    async def test_rate_limited_after_threshold(self, client, test_db):
        user, raw_token = await make_user_with_reset_token(test_db)
 
        for _ in range(5):
            await client.post(
                RESET_PATH,
                json={
                    "identifier": user.email,
                    "reset_token": raw_token,
                    "new_password": NEW_PASSWORD,
                },
            )
 
        response = await client.post(
            RESET_PATH,
            json={
                "identifier": user.email,
                "reset_token": raw_token,
                "new_password": NEW_PASSWORD,
            },
        )
 
        assert response.status_code == 429