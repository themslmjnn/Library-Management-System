from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.auth.router import router as auth_router
from src.core.limiter import ip_limiter
from src.core.logging import setup_logging
from src.user.router_admin import router as user_router_admin
from src.user.router_public import router as user_router_public
from src.user.router_staff import router as user_router_staff

setup_logging()

app = FastAPI(title="Library Management System")

app.state.limiter = ip_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router)
app.include_router(user_router_public)
app.include_router(user_router_staff)
app.include_router(user_router_admin)