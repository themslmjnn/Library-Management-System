
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest
import pytest_asyncio
import structlog.testing

from src.core.config import settings
from src.utils.email import (
    _invite_email_html,
    _invite_email_text,
    _send,
    send_invite_email,
)
 
FAKE_TOKEN = "raw_invite_token_abc123"
FAKE_EMAIL = "invited_user@example.com"
RESEND_URL = "https://api.resend.com/emails"
 
 
def _make_mock_response(status_code: int = 200) -> MagicMock:
    mock_response = MagicMock()
    mock_response.status_code = status_code
 
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.text = f'{{"error": "resend error {status_code}"}}'
    else:
        mock_response.raise_for_status.return_value = None
 
    return mock_response
 
 
def _patch_async_client(mock_response: MagicMock):
    mock_post = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.post = mock_post
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    
    return mock_client_instance, mock_post