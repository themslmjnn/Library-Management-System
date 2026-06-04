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
async def get_all_failed_emails(
    db: async_db_dependency,
    pagination: pagination_dependency,
    _: Annotated[User, Depends(require_system_admin)],
):
    emails, total = await PendingEmailRepository.get_all_failed(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    return PaginatedResponse(
        items=emails,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post("/{email_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def retry_any_failed_email(
    db: async_db_dependency,
    email_id: Annotated[int, Path(ge=1)],
    _: Annotated[User, Depends(require_system_admin)],
):
    record = await PendingEmailRepository.get_by_id(db, email_id)
    ensure_exists(record, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

    await PendingEmailRepository.reset_for_retry(db, record)


@router.get(
    "/my-failed",
    response_model=PaginatedResponse[PendingEmailResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_failed_emails(
    db: async_db_dependency,
    current_user: current_user_dependency,
    pagination: pagination_dependency,
):
    if current_user.role not in (
        UserRole.library_admin,
        UserRole.receptionist,
        UserRole.system_admin,
    ):
        raise AccessDeniedError(HTTP403.ACCESS_DENIED)

    emails, total = await PendingEmailRepository.get_failed_by_triggered_by(
        db,
        triggered_by=current_user.id,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    return PaginatedResponse(
        items=emails,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post("/my-failed/{email_id}/retry", status_code=status.HTTP_204_NO_CONTENT)
async def retry_my_failed_email(
    db: async_db_dependency,
    current_user: current_user_dependency,
    email_id: Annotated[int, Path(ge=1)],
):
    if current_user.role not in (
        UserRole.library_admin,
        UserRole.receptionist,
        UserRole.system_admin,
    ):
        raise AccessDeniedError(HTTP403.ACCESS_DENIED)

    record = await PendingEmailRepository.get_by_id(db, email_id)
    ensure_exists(record, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

    if (
        current_user.role != UserRole.system_admin
        and record.triggered_by != current_user.id
    ):
        raise AccessDeniedError(HTTP403.ACCESS_DENIED)

    await PendingEmailRepository.reset_for_retry(db, record)
