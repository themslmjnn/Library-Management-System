import asyncio

from src.core.logging import get_logger
from src.database import AsyncSessionLocal
from src.email.repository import PendingEmailRepository
from src.utils.email import send

logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 60
BATCH_SIZE = 10


async def _process_batch() -> None:
    async with AsyncSessionLocal() as db:
        pending = await PendingEmailRepository.get_pending(db, limit=BATCH_SIZE)

        if not pending:
            return

        logger.info(
            "email_worker_processing",
            batch_size=len(pending),
        )

        for record in pending:
            try:
                await send(
                    subject=record.subject,
                    to_email=record.recipient,
                    html_body=record.html_body,
                    text_body=record.text_body,
                )

                await PendingEmailRepository.mark_sent(db, record)

                logger.info(
                    "pending_email_sent",
                    email_id=record.id,
                    email_type=record.email_type,
                    recipient_user_id=record.recipient_user_id,
                )

            except Exception as exc:
                await PendingEmailRepository.mark_failed_attempt(db, record, str(exc))

                logger.warning(
                    "pending_email_attempt_failed",
                    email_id=record.id,
                    email_type=record.email_type,
                    retry_count=record.retry_count,
                    error_type=type(exc).__name__,
                    error_repr=repr(exc),
                )

                if record.retry_count >= 3:
                    logger.error(
                        "pending_email_exhausted_retries",
                        email_id=record.id,
                        email_type=record.email_type,
                        recipient_user_id=record.recipient_user_id,
                    )


async def run_email_worker() -> None:
    logger.info(
        "email_worker_started",
        poll_interval=POLL_INTERVAL_SECONDS,
        batch_size=BATCH_SIZE,
    )

    while True:
        try:
            await _process_batch()
        except asyncio.CancelledError:
            logger.info("email_worker_stopping")

            raise
        except Exception as exc:
            logger.error(
                "email_worker_unexpected_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
