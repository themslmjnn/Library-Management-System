from email.service import PendingEmailService
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.core.dependencies import (
    async_db_dependency,
    current_user_dependency,
    pagination_dependency,
    require_system_admin,
)
from src.email.repository import PendingEmailRepository
from src.email.schemas import PendingEmailResponse
from src.pagination import PaginatedResponse
from src.users.models import User
from src.utils.custom_exceptions import AccessDeniedError, PendingEmailNotFoundError
from src.utils.enums import UserRole
from src.utils.exception_constants import HTTP403, HTTP404
from src.utils.helpers import ensure_exists

router = APIRouter(
    prefix="/emails",
    tags=["Emails - Admin"],
)


@router.get(
    "/failed",
    response_model=PaginatedResponse[PendingEmailResponse],
    status_code=status.HTTP_200_OK,
)
async def get_failed_emails(
    db: async_db_dependency,
    pagination: pagination_dependency,
    _: Annotated[User, Depends(require_system_admin)],
):
    return await PendingEmailService.get_failed_emails(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post("/{email_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def retry_failed_email(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    email_id: Annotated[int, Path(ge=1)],
):
    await PendingEmailService.retry_failed_email(db, email_id)


@router.get(
    "/my_failed",
    response_model=PaginatedResponse[PendingEmailResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_failed_emails(
    db: async_db_dependency,
    current_user: current_user_dependency,
    pagination: pagination_dependency,
):
    return await PendingEmailService.get_my_failed_emails(
        db, current_user, skip=pagination.skip, limit=pagination.limit
    )


@router.post("/my-failed/{email_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def retry_my_failed_email(
    db: async_db_dependency,
    current_user: current_user_dependency,
    email_id: Annotated[int, Path(ge=1)],
):
    return await PendingEmailService.retry_my_failed_email(db, current_user, email_id)
