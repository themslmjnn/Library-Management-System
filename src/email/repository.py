from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.enums import EmailSendingStatus
from src.email.models import PendingEmail


class PendingEmailRepository:
    @staticmethod
    def add_pending_email(
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

    @staticmethod
    async def _count_failed(db: AsyncSession) -> int:
        query = select(func.count()).select_from(
            select(PendingEmail).where(PendingEmail.status == "failed").subquery()
        )

        result = await db.execute(query)

        return result.scalar_one()

    @staticmethod
    async def get_pending_emails(
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
    async def get_failed_emails(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[PendingEmail], int]:
        total = await PendingEmailRepository._count_failed(db)

        query = (
            select(PendingEmail)
            .where(PendingEmail.status == "failed")
            .order_by(PendingEmail.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)

        return list(result.scalars().all()), total

    @staticmethod
    async def get_failed_by_triggered_by(
        db: AsyncSession,
        triggered_by: int,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[PendingEmail], int]:
        count_query = select(func.count()).select_from(
            select(PendingEmail)
            .where(
                PendingEmail.status == "failed",
                PendingEmail.triggered_by == triggered_by,
            )
            .subquery()
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        query = (
            select(PendingEmail)
            .where(
                PendingEmail.status == "failed",
                PendingEmail.triggered_by == triggered_by,
            )
            .order_by(PendingEmail.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)

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
        record.status = "pending"
        record.retry_count = 0
        record.last_error = None

        await db.commit()
