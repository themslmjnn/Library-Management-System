from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        """
        Fetches pending emails that have not exceeded retry limit.
        Ordered oldest first so nothing starves.
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
    async def get_failed(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[PendingEmail], int]:
        """
        Returns emails that exhausted all retries.
        Used by the admin endpoint.
        """
        from sqlalchemy import func, select

        count_result = await db.execute(
            select(func.count()).select_from(
                select(PendingEmail).where(PendingEmail.status == "failed").subquery()
            )
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(PendingEmail)
            .where(PendingEmail.status == "failed")
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
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def mark_failed_attempt(
        db: AsyncSession,
        record: PendingEmail,
        error: str,
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
        Admin-triggered retry: reset a failed email back to pending.
        """
        record.status = "pending"
        record.retry_count = 0
        record.last_error = None
        await db.commit()
