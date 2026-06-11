from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import CurrentUser
from pagination import PaginatedResponse
from src.email.repository import PendingEmailRepository
from utils.custom_exceptions import AccessDeniedError, PendingEmailNotFoundError
from utils.enums import UserRole
from utils.exception_constants import HTTP403, HTTP404
from utils.helpers import ensure_exists


class PendingEmailService:
    @staticmethod
    async def get_failed_emails(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
    ) -> PaginatedResponse:
        failed_emails, total = await PendingEmailRepository.get_failed_emails(
            db,
            skip=skip,
            limit=limit,
        )

        return PaginatedResponse(
            items=failed_emails,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )

    @staticmethod
    async def retry_failed_email(
        db: AsyncSession,
        email_id: int,
    ) -> None:
        failed_email = await PendingEmailRepository.get_pending_email_by_id(
            db, email_id
        )
        ensure_exists(failed_email, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

        await PendingEmailRepository.reset_for_retry(db, failed_email)

    @staticmethod
    async def get_my_failed_emails(
        db: AsyncSession,
        current_user: CurrentUser,
        skip: int = 0,
        limit: int = 10,
    ) -> PaginatedResponse:
        if current_user.role not in (
            UserRole.library_admin,
            UserRole.receptionist,
            UserRole.system_admin,
        ):
            raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        failed_emails, total = await PendingEmailRepository.get_failed_by_triggered_by(
            db,
            triggered_by=current_user.id,
            skip=skip,
            limit=limit,
        )

        return PaginatedResponse(
            items=failed_emails,
            total=total,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    async def retry_my_failed_email(
        db: AsyncSession,
        current_user: CurrentUser,
        email_id: int,
    ) -> None:
        if current_user.role not in (
            UserRole.library_admin,
            UserRole.receptionist,
            UserRole.system_admin,
        ):
            raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        failed_email = await PendingEmailRepository.get_by_id(db, email_id)
        ensure_exists(failed_email, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

        if (
            current_user.role != UserRole.system_admin
            and failed_email.triggered_by != current_user.id
        ):
            raise AccessDeniedError(HTTP403.ACCESS_DENIED)

        await PendingEmailRepository.reset_for_retry(db, failed_email)
