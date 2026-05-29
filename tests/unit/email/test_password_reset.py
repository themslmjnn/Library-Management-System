# from datetime import datetime, timedelta, timezone
# from unittest.mock import AsyncMock, patch

# import pytest
# import pytest_asyncio
# import structlog.testing
# from httpx import ASGITransport, AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession

# from src.modules.auth.exceptions import (
#     ExpiredResetPasswordTokenError,
#     InvalidCredentialsError,
#     InvalidResetPasswordTokenError,
# )
# from src.modules.auth.schemas import CreateResetPasswordRequest, ResetPasswordRequest
# from src.modules.auth.service import AuthService
# from src.modules.users.repository import UserRepositoryBase
# from src.utils.security import generate_reset_password_token, hash_password
from src.core.config import settings
from src.utils.email import (
    _reset_password_html,
    _reset_password_text,
    # send_reset_password_token,
)

# from tests.conftest import (
#     CORRECT_PASSWORD,
#     NEW_PASSWORD,
#     make_auth_header,
#     make_member,
# )
from tests.constants import FAKE_RESET_TOKEN


class TestResetPasswordHtml:
    def test_token_appears_in_body(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in html

    def test_reset_link_contains_app_url(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert settings.APP_URL in html

    def test_reset_link_has_token_query_param(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert f"token={FAKE_RESET_TOKEN}" in html

    def test_reset_link_points_to_reset_page_not_request_endpoint(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)
        expected = f"{settings.APP_URL}/reset_password?token={FAKE_RESET_TOKEN}"

        assert expected in html

    def test_expiry_minutes_mentioned(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in html

    def test_is_valid_html_string(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "</html>" in html

    def test_token_appears_in_href(self):
        html = _reset_password_html(FAKE_RESET_TOKEN)

        assert 'href="' in html
        assert f"token={FAKE_RESET_TOKEN}" in html

    def test_different_tokens_produce_different_links(self):
        html_a = _reset_password_html("token_aaa")
        html_b = _reset_password_html("token_bbb")

        assert html_a != html_b


class TestResetPasswordText:
    def test_token_appears_in_body(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert FAKE_RESET_TOKEN in text

    def test_reset_link_contains_app_url(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert settings.APP_URL in text

    def test_reset_link_has_token_query_param(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert f"token={FAKE_RESET_TOKEN}" in text

    def test_reset_link_points_to_reset_page_not_request_endpoint(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)
        expected = f"{settings.APP_URL}/reset_password?token={FAKE_RESET_TOKEN}"

        assert expected in text

    def test_expiry_minutes_mentioned(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert str(settings.RESET_PASSWORD_EXPIRES_MINUTES) in text

    def test_is_plain_text_no_html_tags(self):
        text = _reset_password_text(FAKE_RESET_TOKEN)

        assert "<" not in text
        assert ">" not in text

    def test_different_tokens_produce_different_links(self):
        text_a = _reset_password_text("token_aaa")
        text_b = _reset_password_text("token_bbb")

        assert text_a != text_b

    def test_html_and_text_share_identical_reset_link(self):
        token = "consistent_token_xyz"
        expected_link = f"{settings.APP_URL}/reset_password?token={token}"

        assert expected_link in _reset_password_html(token)
        assert expected_link in _reset_password_text(token)
