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
        record = PendingEmail(
            recipient=recipient,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            email_type=email_type,
            status=EmailSendingStatus.pending,
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
        """
        Fetches pending emails that still have retries remaining.
        Ordered by created_at ascending — oldest first so nothing starves.
        Called by the background worker every poll cycle.
        """
        result = await db.execute(
            select(PendingEmail)
            .where(
                PendingEmail.status == "pending",
                PendingEmail.retry_count < 3,
            )
            .order_by(PendingEmail.created_at.asc())
            .limit(limit)
        )
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
    async def get_by_id(
        db: AsyncSession,
        email_id: int,
    ) -> PendingEmail | None:
        result = await db.execute(
            select(PendingEmail).where(PendingEmail.id == email_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_sent(
        db: AsyncSession,
        record: PendingEmail,
    ) -> None:
        """Called by worker after successful send."""
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def mark_failed_attempt(
        db: AsyncSession,
        record: PendingEmail,
        error: str,
    ) -> None:
        """
        Called by worker after a failed send attempt.
        Increments retry_count and records the error.
        If retry_count reaches 3 the status becomes "failed"
        and the worker will no longer attempt it automatically.
        """
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
            select(PendingEmail)
            .where(PendingEmail.status == "failed")
            .subquery()
        )
    )
    return result.scalar_one()