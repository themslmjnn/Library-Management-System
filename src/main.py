import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.auth.router import router as auth_router
from src.books.router import router as book_router
from src.core.cache import redis_client
from src.core.config import settings
from src.core.email_worker import run_email_worker
from src.core.limiter import ip_limiter
from src.core.logging import get_logger, setup_logging
from src.email.router import router as email_router
from src.inventories.router import router as inventory_router
from src.loans.router import router as loan_staff_router
from src.loans.router_public import router as loan_router_public
from src.users.router_admin import router as user_router_admin
from src.users.router_public import router as user_router_public
from src.users.router_staff import router as user_router_staff
from src.utils import custom_exceptions as exc

setup_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_client.ping()

        logger.info("redis_connected")
    except Exception as e:
        logger.warning(
            "redis_unavailable",
            error=str(e),
        )

    email_worker_task = asyncio.create_task(run_email_worker())

    logger.info("email_worker_task_started")

    yield

    email_worker_task.cancel()
    try:
        await email_worker_task
    except (asyncio.CancelledError, Exception):
        logger.info("email_worker_stopped")
        raise

    await redis_client.aclose()

    logger.info("redis_disconnected")


app = FastAPI(
    title="Library Management System",
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
)

app.state.limiter = ip_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


app.include_router(auth_router)
app.include_router(user_router_public)
app.include_router(user_router_staff)
app.include_router(user_router_admin)
# app.include_router(book_router)
# app.include_router(inventory_router)
# app.include_router(loan_router_public)
# app.include_router(loan_staff_router)
app.include_router(email_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

EXCEPTION_STATUS_MAP = {
    exc.UserNotFoundError: 404,
    exc.BookNotFoundError: 404,
    exc.InventoryNotFoundError: 404,
    exc.LoanNotFoundError: 404,
    exc.UserAlreadyActiveError: 409,
    exc.UserAlreadyInactiveError: 409,
    exc.BookAlreadyExistsError: 409,
    exc.LoanAlreadyReturnedError: 409,
    exc.UserAlreadyHasActiveLoanError: 409,
    exc.BookNotAvailableError: 409,
    exc.InvalidCredentialsError: 401,
    exc.InvalidInviteTokenError: 400,
    exc.ExpiredInviteTokenError: 400,
    exc.InvalidRefreshTokenError: 401,
    exc.ExpiredRefreshTokenError: 401,
    exc.InvalidActivationCodeError: 400,
    exc.ExpiredActivationCodeError: 400,
    exc.AccountLockedError: 403,
    exc.AccountInactiveError: 403,
    exc.CannotCreateSystemAdminError: 403,
    exc.CannotAssignSystemRoleError: 403,
    exc.IncorrectPasswordError: 400,
    exc.EmailAlreadyTakenError: 409,
    exc.UsernameAlreadyTakenError: 409,
    exc.PhonenumberAlreadyTakenError: 409,
    exc.EmptyCredentialsError: 400,
    exc.InvalidAccessTokenError: 401,
    exc.AccessDeniedError: 403,
    exc.InvalidResetPasswordTokenError: 400,
    exc.ExpiredResetPasswordTokenError: 400,
    exc.PendingEmailNotFoundError: 404,
    exc.InvalidEmailChangeCodeError: 400,
    exc.ExpiredEmailChangeCodeError: 400,
}


@app.exception_handler(exc.AppException)
async def app_exception_handler(
    request: Request, exc: exc.AppException
) -> JSONResponse:
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"},
    )
