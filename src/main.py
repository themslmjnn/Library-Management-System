from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.auth.router import router as auth_router
from src.book.router import router as book_router
from src.core.limiter import ip_limiter
from src.core.logging import setup_logging
from src.inventory.router import router as inventory_router
from src.loan.router import router as loan_staff_router
from src.loan.router_public import router as loan_router_public
from src.user.router_admin import router as user_router_admin
from src.user.router_public import router as user_router_public
from src.user.router_staff import router as user_router_staff
from src.core.logging import get_logger
from src.core.cache import redis_client

setup_logging()

logger = get_logger(__name__)

app = FastAPI(title="Library Management System")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # everything before yield runs on startup
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    yield  # app runs here

    # everything after yield runs on shutdown
    await redis_client.aclose()
    logger.info("redis_disconnected")

app.state.limiter = ip_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router)
app.include_router(user_router_public)
app.include_router(user_router_staff)
app.include_router(user_router_admin)
app.include_router(book_router)
app.include_router(inventory_router)
app.include_router(loan_router_public)
app.include_router(loan_staff_router)