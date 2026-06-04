# src/email/repository.py

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailSendingStatus
from src.email.models import PendingEmail


class PendingEmailRepository:
    @staticmethod
    def create(
        db: AsyncSession,
        *,
        recipient: str,
        subject: str,
        html_body: str,
        text_body: str,
        email_type: str,
        triggered_by: int | None = None,
        recipient_user_id: int | None = None,
    ) -> PendingEmail:
        """
        Adds a PendingEmail to the session WITHOUT flushing or committing.

        The caller controls the transaction. This means the email record
        is inserted atomically with whatever else the caller is doing —
        user creation, token write, etc. Either everything commits or
        nothing does.
        """
        record = PendingEmail(
            recipient=recipient,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=email_type,
            status="pending",
            triggered_by=triggered_by,
            recipient_user_id=recipient_user_id,
        )
        db.add(record)
        return record

    @staticmethod
    async def get_pending(
        db: AsyncSession,
        limit: int = 10,
    ) -> list[PendingEmail]:
        query = (
            select(PendingEmail)
            .where(
                PendingEmail.status == EmailSendingStatus.pending,
                PendingEmail.retry_count < 3,
            )
            .order_by(PendingEmail.created_at.asc())
            .limit(limit)
        )

        result = await db.execute(query)

        return list(result.scalars().all())

    @staticmethod
    async def get_all_failed(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[PendingEmail], int]:
        """
        Returns all failed emails regardless of who triggered them.
        Used by system admin endpoint.
        """
        total = await _count_failed(db)
        result = await db.execute(
            select(PendingEmail)
            .where(PendingEmail.status == "failed")
            .order_by(PendingEmail.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_failed_by_triggered_by(
        db: AsyncSession,
        triggered_by: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[PendingEmail], int]:
        """
        Returns failed emails triggered by a specific staff member.
        Used by library admin endpoint — they see only their own.
        """
        count_result = await db.execute(
            select(func.count()).select_from(
                select(PendingEmail)
                .where(
                    PendingEmail.status == "failed",
                    PendingEmail.triggered_by == triggered_by,
                )
                .subquery()
            )
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(PendingEmail)
            .where(
                PendingEmail.status == "failed",
                PendingEmail.triggered_by == triggered_by,
            )
            .order_by(PendingEmail.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_pending_email_by_id(
        db: AsyncSession, email_id: int
    ) -> PendingEmail | None:
        query = select(PendingEmail).filter(PendingEmail.id == email_id)

        result = await db.execute(query)

        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_email_by_triggered_by(
        db: AsyncSession, triggered_by: int | None
    ) -> list[PendingEmail]:
        query = select(PendingEmail).filter(PendingEmail.triggered_by == triggered_by)

        result = await db.execute(query)

        return result.scalars().all()

    @staticmethod
    async def mark_sent(db: AsyncSession, record: PendingEmail) -> None:
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)

        await db.commit()

    @staticmethod
    async def mark_failed_attempt(
        db: AsyncSession, record: PendingEmail, error: str
    ) -> None:
        record.retry_count += 1
        record.last_error = error

        if record.retry_count >= 3:
            record.status = "failed"

        await db.commit()

    @staticmethod
    async def reset_for_retry(
        db: AsyncSession,
        record: PendingEmail,
    ) -> None:
        """
        Admin-triggered retry. Resets a failed record back to pending.
        The worker picks it up on the next poll cycle (within 60 seconds).
        """
        record.status = "pending"
        record.retry_count = 0
        record.last_error = None
        await db.commit()


async def _count_failed(db: AsyncSession) -> int:
    """Private helper — counts all failed emails for pagination."""
    result = await db.execute(
        select(func.count()).select_from(
            select(PendingEmail).where(PendingEmail.status == "failed").subquery()
        )
    )
    return result.scalar_one()
