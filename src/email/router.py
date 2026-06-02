# src/email/router.py

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from src.core.dependencies import (
    async_db_dependency,
    current_user_dependency,
    pagination_dependency,
    require_system_admin,
    require_system_and_library_admin,
)
from src.email.repository import PendingEmailRepository
from src.users.models import User
from src.utils.custom_exceptions import PendingEmailNotFoundError
from src.utils.enums import UserRole
from src.utils.exception_constants import HTTP403, HTTP404
from src.utils.exceptions import AccessDeniedError
from src.utils.helpers import ensure_exists
from src.utils.pagination import PaginatedResponse

router = APIRouter(
    prefix="/emails",
    tags=["Emails - Admin"],
)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class PendingEmailResponse(BaseModel):
    """
    What the admin sees when viewing a pending or failed email record.
    Does not expose html_body or text_body — they can be large and
    are not useful for the admin to see in a list view.
    """
    id: int
    recipient: str
    subject: str
    email_type: str
    status: str
    retry_count: int
    last_error: str | None
    sent_at: str | None
    triggered_by: int | None
    recipient_user_id: int | None
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# System admin endpoints — all failed emails
# ---------------------------------------------------------------------------

@router.get(
    "/failed",
    response_model=PaginatedResponse[PendingEmailResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_system_admin)],
)
async def get_all_failed_emails(
    db: async_db_dependency,
    pagination: pagination_dependency,
):
    """
    System admin only.
    Returns all emails that exhausted 3 retry attempts.
    Use the retry endpoint to re-queue individual records.
    """
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


@router.post(
    "/{email_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_system_admin)],
)
async def retry_any_failed_email(
    db: async_db_dependency,
    email_id: Annotated[int, Path(ge=1)],
):
    """
    System admin only.
    Resets a failed email record back to pending with retry_count=0.
    The worker picks it up within the next poll cycle (60 seconds).
    """
    record = await PendingEmailRepository.get_by_id(db, email_id)
    ensure_exists(record, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

    await PendingEmailRepository.reset_for_retry(db, record)


# ---------------------------------------------------------------------------
# Library admin endpoints — only their own triggered emails
# ---------------------------------------------------------------------------

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
    """
    Library admin and receptionist.
    Returns only failed emails that the current user triggered.

    A library admin who created a user and whose invite email failed
    can see it here and retry it.
    """
    # require_system_and_library_admin allows system_admin too —
    # but system_admin should use /failed instead (sees everything).
    # We guard at service level to keep roles clean.
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


@router.post(
    "/my-failed/{email_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def retry_my_failed_email(
    db: async_db_dependency,
    current_user: current_user_dependency,
    email_id: Annotated[int, Path(ge=1)],
):
    """
    Library admin and receptionist.
    Retries a failed email — but only if they triggered it.

    Fetches the record first and verifies triggered_by matches
    the current user. This prevents a library admin from retrying
    another admin's emails by guessing IDs.
    """
    if current_user.role not in (
        UserRole.library_admin,
        UserRole.receptionist,
        UserRole.system_admin,
    ):
        raise AccessDeniedError(HTTP403.ACCESS_DENIED)

    record = await PendingEmailRepository.get_by_id(db, email_id)
    ensure_exists(record, PendingEmailNotFoundError(HTTP404.PENDING_EMAIL))

    # Ownership check — library admin can only retry their own emails.
    # System admin bypasses this check — they can retry anything via /emails/{id}/retry.
    if (
        current_user.role != UserRole.system_admin
        and record.triggered_by != current_user.id
    ):
        raise AccessDeniedError(HTTP403.ACCESS_DENIED)

    await PendingEmailRepository.reset_for_retry(db, record)