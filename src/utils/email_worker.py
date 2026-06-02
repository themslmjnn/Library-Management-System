# src/core/email_worker.py

import asyncio

from src.core.logging import get_logger
from src.database import AsyncSessionLocal
from src.email.repository import PendingEmailRepository
from src.utils.email import _send

logger = get_logger(__name__)

# How often the worker checks for pending emails (seconds).
# 60 seconds means a newly inserted email is sent within 1 minute.
POLL_INTERVAL_SECONDS = 60

# How many emails to process per cycle.
# Keeps each cycle bounded — if 1000 emails are pending,
# we process them in batches rather than all at once.
BATCH_SIZE = 10


async def _process_batch() -> None:
    """
    Opens its own database session, fetches a batch of pending emails,
    and attempts to send each one.

    Uses a fresh session per cycle — completely independent of any
    request session. This means request failures never affect the
    worker and vice versa.

    Each email is committed individually after success or failure.
    This means if the worker crashes mid-batch, already-sent emails
    are marked sent and won't be retried. Unprocessed ones remain
    pending and are picked up on the next cycle.
    """
    async with AsyncSessionLocal() as db:
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

                # Mark as sent — committed immediately so this record
                # is not picked up again on the next cycle.
                await PendingEmailRepository.mark_sent(db, record)

                logger.info(
                    "pending_email_sent",
                    email_id=record.id,
                    email_type=record.email_type,
                    recipient_user_id=record.recipient_user_id,
                )

            except Exception as exc:
                # Increment retry_count and record the error.
                # If retry_count reaches 3, status becomes "failed".
                # Committed immediately so the retry count is persisted
                # even if the worker crashes on the next record.
                await PendingEmailRepository.mark_failed_attempt(
                    db, record, str(exc)
                )

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
    Long-running coroutine. Started as an asyncio task in the FastAPI
    lifespan and cancelled on shutdown.

    The outer try/except ensures the worker never crashes permanently —
    if _process_batch raises something unexpected, the error is logged
    and the worker sleeps then tries again.

    asyncio.CancelledError is NOT caught here — it must propagate so
    the lifespan shutdown can await the cancellation cleanly.
    """
    logger.info(
        "email_worker_started",
        poll_interval=POLL_INTERVAL_SECONDS,
        batch_size=BATCH_SIZE,
    )

    while True:
        try:
            await _process_batch()
        except asyncio.CancelledError:
            # Re-raise so the lifespan can detect the task ended cleanly.
            logger.info("email_worker_stopping")
            raise
        except Exception as exc:
            # Unexpected error in the worker itself — log and keep running.
            # We never want the worker to die silently.
            logger.error(
                "email_worker_unexpected_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )

        await asyncio.sleep(POLL_INTERVAL_SECONDS)