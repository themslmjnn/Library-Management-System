from unittest.mock import MagicMock

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.core.cache as cache_module
from src.auth.schemas import CreateAccessTokenRequest
from src.core.config import settings
from src.core.dependencies import get_db
from src.core.limiter import ip_limiter
from src.core.security import create_access_token
from src.database import Base
from src.main import app
from src.user.models import User, UserRole
from tests.factories import (
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
    make_user,
)


# async engine for tests — uses asyncpg
ASYNC_DB_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# sync engine only for table creation — uses psycopg2
SYNC_DB_URL = (
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# async engine used by all test fixtures
test_engine = create_async_engine(
    url=ASYNC_DB_URL,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session", autouse=True)
def create_tables():
    sync_engine = create_engine(SYNC_DB_URL)
    Base.metadata.create_all(sync_engine)

    yield

    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    async with test_engine.connect() as conn:
        await conn.begin()

        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
        )

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db

        yield session

        await session.close()
        await conn.rollback()
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


def make_auth_header(user: User) -> dict:
    token = create_access_token(
        CreateAccessTokenRequest(
            user_id=user.id,
            role=user.role,
            access_token_version=user.access_token_version,
        )
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def system_admin(test_db):
    return await make_system_admin(test_db)


@pytest_asyncio.fixture
async def library_admin(test_db):
    return await make_library_admin(test_db)


@pytest_asyncio.fixture
async def receptionist(test_db):
    return await make_receptionist(test_db)


@pytest_asyncio.fixture
async def member(test_db):
    return await make_member(test_db)


@pytest_asyncio.fixture
async def guest(test_db):
    return await make_user(test_db, role=UserRole.guest)


@pytest.fixture
def mock_response():
    return MagicMock()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    ip_limiter._storage.reset()

    yield


@pytest_asyncio.fixture(autouse=True)
async def flush_cache():
    fresh_client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        db=settings.REDIS_DB,
        decode_responses=True,
    )

    cache_module.redis_client = fresh_client
    await fresh_client.flushdb()

    yield

    await fresh_client.flushdb()
    await fresh_client.aclose()

DEFAULT_PASSWORD = "Valid123!"
CORRECT_PASSWORD = "Correct123!"
WRONG_PASSWORD = "Wrong123!"
NEW_PASSWORD = "NewPassword123!"