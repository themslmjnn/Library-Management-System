import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.schemas import CreateBook
from src.user.models import User, UserRole
from src.utils.exceptions import BookNotFoundError
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_library_admin,
    make_member,
    make_receptionist,
    make_system_admin,
)


class TestGetBooks:
    async def test_public_access_returns_200(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, created_by=system_admin.id)

        response = await client.get("/books")

        assert response.status_code == 200


    async def test_returns_paginated_shape(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, created_by=system_admin.id)

        response = await client.get("/books")
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data


    async def test_pagination_params_work(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        for _ in range(5):
            await make_book(test_db, created_by=system_admin.id)

        response = await client.get("/books?skip=0&limit=2")
        data = response.json()

        assert len(data["items"]) == 2
        assert data["has_more"] is True


    async def test_category_filter_works(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, category="fiction", created_by=system_admin.id)
        await make_book(test_db, category="fiction", created_by=system_admin.id)
        await make_book(test_db, category="science", created_by=system_admin.id)

        response = await client.get("/books?category=fiction")
        data = response.json()

        assert data["total"] == 2
        assert all(b["category"] == "fiction" for b in data["items"])


    async def test_title_search_works(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, title="Django Unleashed", created_by=system_admin.id)
        await make_book(test_db, title="Flask Web Dev", created_by=system_admin.id)

        response = await client.get("/books?title=django")
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["title"] == "Django Unleashed"


    async def test_sort_order_works(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, title="Zebra", created_by=system_admin.id)
        await make_book(test_db, title="Apple", created_by=system_admin.id)

        response = await client.get("/books?sort_by=title&order=asc")
        data = response.json()

        titles = [b["title"] for b in data["items"]]
        assert titles == sorted(titles)


    async def test_empty_result_for_no_match(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        await make_book(test_db, created_by=system_admin.id)

        response = await client.get("/books?title=zzz_no_match_zzz")
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []


class TestGetBookById:
    async def test_public_access_returns_200(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        response = await client.get(f"/books/{book.id}")

        assert response.status_code == 200


    async def test_returns_correct_fields(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        response = await client.get(f"/books/{book.id}")
        data = response.json()

        assert data["id"] == book.id
        assert data["title"] == book.title
        assert data["author"] == book.author
        assert data["category"] == book.category


    async def test_returns_404_for_unknown_id(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        response = await client.get(f"/books/{book.id + 999999}")

        assert response.status_code == 404


    async def test_second_request_returns_same_data(self, client: AsyncClient, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        r1 = await client.get(f"/books/{book.id}")
        r2 = await client.get(f"/books/{book.id}")

        assert r1.json() == r2.json()