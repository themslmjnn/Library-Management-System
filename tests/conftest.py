from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

test_engine = create_async_engine(
    url=TEST_DB_URL,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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