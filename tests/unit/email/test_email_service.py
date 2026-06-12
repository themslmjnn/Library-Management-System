import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailSendingStatus, EmailType
from src.email.models import PendingEmail
from src.email.service import PendingEmailService
from src.users.models import User
from src.utils.custom_exceptions import AccessDeniedError, PendingEmailNotFoundError
from src.utils.enums import UserRole
from tests.conftest import make_auth_header
from tests.factories import (
    make_failed_email,
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
)


class TestGetFailedEmails:
    async def test_returns_paginated_response(self, test_db: AsyncSession):
        await make_failed_email(test_db)
        await make_failed_email(test_db)
 
        result = await PendingEmailService.get_failed_emails(test_db, skip=0, limit=10)
 
        assert result.total == 2
        assert len(result.items) == 2
        assert result.has_more is False
 
    async def test_has_more_is_true_when_more_pages_exist(self, test_db: AsyncSession):
        for _ in range(5):
            await make_failed_email(test_db)
 
        result = await PendingEmailService.get_failed_emails(test_db, skip=0, limit=2)
 
        assert result.has_more is True
        assert len(result.items) == 2
 
    async def test_skip_offsets_results(self, test_db: AsyncSession):
        for _ in range(4):
            await make_failed_email(test_db)
 
        result = await PendingEmailService.get_failed_emails(test_db, skip=3, limit=10)
 
        assert len(result.items) == 1
 
    async def test_does_not_return_pending_emails(self, test_db: AsyncSession):
        await make_failed_email(test_db, status="pending")
 
        result = await PendingEmailService.get_failed_emails(test_db, skip=0, limit=10)
 
        assert result.total == 0
        assert result.items == []
 
 
class TestRetryFailedEmail:
    async def test_resets_failed_email_for_retry(self, test_db: AsyncSession):
        email = await make_failed_email(test_db)
 
        await PendingEmailService.retry_failed_email(test_db, email.id)
 
        await test_db.refresh(email)
        
        assert email.status == EmailSendingStatus.pending
        assert email.retry_count == 0
        assert email.last_error is None
 
    async def test_raises_not_found_for_nonexistent_email(self, test_db: AsyncSession):
        email = await make_failed_email(test_db)
        non_existent_id = email.id + 999999
 
        with pytest.raises(PendingEmailNotFoundError):
            await PendingEmailService.retry_failed_email(test_db, non_existent_id)
 
 
class TestGetMyFailedEmails:
    @pytest.mark.parametrize("make_staff", [
        make_library_admin,
        make_receptionist,
        make_system_admin,
    ])
    async def test_allowed_roles_return_own_failed_emails(
        self, test_db: AsyncSession, make_staff
    ):
        user = await make_staff(test_db)
        await make_failed_email(test_db, triggered_by=user.id)
 
        result = await PendingEmailService.get_my_failed_emails(
            test_db, user, skip=0, limit=10
        )
 
        assert result.total == 1
        assert result.items[0].triggered_by == user.id
 
    async def test_member_raises_access_denied(self, test_db: AsyncSession):
        user = await make_member(test_db)
 
        with pytest.raises(AccessDeniedError):
            await PendingEmailService.get_my_failed_emails(test_db, user)
 
    async def test_does_not_return_other_users_emails(self, test_db: AsyncSession):
        user = await make_library_admin(test_db)
        other = await make_library_admin(test_db)
        await make_failed_email(test_db, triggered_by=other.id)
 
        result = await PendingEmailService.get_my_failed_emails(
            test_db, user, skip=0, limit=10
        )
 
        assert result.total == 0
 
    async def test_has_more_is_true_when_more_pages_exist(self, test_db: AsyncSession):
        user = await make_library_admin(test_db)
        for _ in range(5):
            await make_failed_email(test_db, triggered_by=user.id)
 
        result = await PendingEmailService.get_my_failed_emails(
            test_db, user, skip=0, limit=2
        )
 
        assert result.has_more is True