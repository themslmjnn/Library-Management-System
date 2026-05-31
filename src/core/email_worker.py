import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database import AsyncSessionLocal
from src.email.repository import PendingEmailRepository
from utils.email import _send

logger = get_logger(__name__)

# How often the worker polls the pending_emails table (seconds)
POLL_INTERVAL_SECONDS = 60

# How many emails to process per poll cycle
BATCH_SIZE = 10


async def _process_batch(db: AsyncSession) -> None:
    """
    Fetches a batch of pending emails and attempts to send each one.
    Marks each record as sent or increments retry_count on failure.
    After 3 failed attempts the record is marked as "failed" and
    stops being retried — visible to admins via GET /admin/emails/failed.
    """
    pending = await PendingEmailRepository.get_pending(db, limit=BATCH_SIZE)

    if not pending:
        return

    logger.info("email_worker_processing", batch_size=len(pending))

    for record in pending:
        try:
            await _send(
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
                error=str(exc),
            )

            if record.retry_count >= 3:
                logger.error(
                    "pending_email_exhausted_retries",
                    email_id=record.id,
                    email_type=record.email_type,
                    recipient_user_id=record.recipient_user_id,
                )


async def run_email_worker() -> None:
    """
    Long-running coroutine. Polls pending_emails every POLL_INTERVAL_SECONDS.
    Runs as an asyncio task started in the FastAPI lifespan.
    Creates its own DB session per cycle — independent of request sessions.
    """
    logger.info("email_worker_started", poll_interval=POLL_INTERVAL_SECONDS)

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await _process_batch(db)
        except Exception as exc:
            # Worker itself should never crash — log and keep running
            logger.error("email_worker_error", error=str(exc))

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Updated main.py lifespan — replace your existing lifespan with this
# ---------------------------------------------------------------------------

# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from src.core.cache import redis_client
# from src.core.logging import get_logger
# from src.core.email_worker import run_email_worker
#
# logger = get_logger(__name__)
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     try:
#         await redis_client.ping()
#         logger.info("redis_connected")
#     except Exception as e:
#         logger.warning("redis_unavailable", error=str(e))
#
#     # Start the email worker as a background task
#     email_worker_task = asyncio.create_task(run_email_worker())
#     logger.info("email_worker_task_started")
#
#     yield
#
#     # Shutdown
#     email_worker_task.cancel()
#     try:
#         await email_worker_task
#     except asyncio.CancelledError:
#         logger.info("email_worker_stopped")
#
#     await redis_client.aclose()
#     logger.info("redis_disconnected")
