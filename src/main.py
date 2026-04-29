from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.auth.router import router as auth_router
from src.book.router import router as book_router
from src.core.cache import redis_client
from src.core.limiter import ip_limiter
from src.core.logging import get_logger, setup_logging
from src.inventory.router import router as inventory_router
from src.loan.router import router as loan_staff_router
from src.loan.router_public import router as loan_router_public
from src.user.router_admin import router as user_router_admin
from src.user.router_public import router as user_router_public
from src.user.router_staff import router as user_router_staff
from src.utils.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    AppException,
    BookAlreadyExistsError,
    BookNotAvailableError,
    BookNotFoundError,
    CannotAssignSystemRoleError,
    CannotCreateSystemAdminError,
    ExpiredActivationCodeError,
    ExpiredInviteTokenError,
    ExpiredRefreshTokenError,
    IncorrectPasswordError,
    InvalidActivationCodeError,
    InvalidCredentialsError,
    InvalidInviteTokenError,
    InvalidRefreshTokenError,
    InventoryNotFoundError,
    LoanAlreadyReturnedError,
    LoanNotFoundError,
    UserAlreadyActiveError,
    UserAlreadyHasActiveLoanError,
    UserAlreadyInactiveError,
    UserNotFoundError,
)

setup_logging()

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    yield

    await redis_client.aclose()
    logger.info("redis_disconnected")

app = FastAPI(
    title="Library Management System",
    lifespan=lifespan,
)


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


EXCEPTION_STATUS_MAP = {
    UserNotFoundError:              404,
    BookNotFoundError:              404,
    InventoryNotFoundError:         404,
    LoanNotFoundError:              404,
    UserAlreadyActiveError:         409,
    UserAlreadyInactiveError:       409,
    BookAlreadyExistsError:         409,
    LoanAlreadyReturnedError:       409,
    UserAlreadyHasActiveLoanError:  409,
    BookNotAvailableError:          409,
    InvalidCredentialsError:        401,
    InvalidInviteTokenError:        400,
    ExpiredInviteTokenError:        400,
    InvalidRefreshTokenError:       401,
    ExpiredRefreshTokenError:       401,
    InvalidActivationCodeError:     400,
    ExpiredActivationCodeError:     400,
    AccountLockedError:             403,
    AccountInactiveError:           403,
    CannotCreateSystemAdminError:   403,
    CannotAssignSystemRoleError:    403,
    IncorrectPasswordError:         400,
}

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.detail},
    )