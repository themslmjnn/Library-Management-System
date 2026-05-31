# src/email/router.py
#
# Admin-only endpoint for viewing and retrying failed emails.
# Add this router to main.py:
#   from src.email.router import router as email_router
#   app.include_router(email_router)

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_system_admin,
)
from src.email.repository import PendingEmailRepository
from src.pagination import PaginatedResponse
from src.users.models import User
from src.utils.custom_exceptions import UserNotFoundError
from src.utils.exception_constants import HTTP404
from src.utils.helpers import ensure_exists

router = APIRouter(
    prefix="/admin/emails",
    tags=["Admin - Emails"],
)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PendingEmailResponse(BaseModel):
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
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/failed",
    response_model=PaginatedResponse[PendingEmailResponse],
    status_code=status.HTTP_200_OK,
    summary="List all emails that exhausted retries",
    description=(
        "Returns emails that failed all 3 send attempts. "
        "Use the retry endpoint to re-queue individual records."
    ),
)
async def get_failed_emails(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    pagination: pagination_dependency,
):
    emails, total = await PendingEmailRepository.get_failed(
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
    summary="Re-queue a failed email for sending",
    description=(
        "Resets a failed email record back to pending with retry_count=0. "
        "The email worker will pick it up within the next poll cycle (60 seconds)."
    ),
)
async def retry_failed_email(
    db: async_db_dependency,
    _: Annotated[User, Depends(require_system_admin)],
    email_id: Annotated[int, Path(ge=1)],
):
    record = await PendingEmailRepository.get_by_id(db, email_id)
    ensure_exists(record, UserNotFoundError(HTTP404.USER))  # reuse 404 pattern

    await PendingEmailRepository.reset_for_retry(db, record)
