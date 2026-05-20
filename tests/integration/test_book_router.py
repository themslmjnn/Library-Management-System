from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_member,
)


class TestCreateBook:
    async def test_system_admin_creates_book(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "title": "New Book",
            "author": "New Author",
            "category": "science",
            "description": "A great book",
            "publishing_date": "2020-01-01",
        }

        response = await client.post("/books", json=payload, headers=headers)

        data = response.json()

        assert response.status_code == 201
        assert data["title"] == "New Book"
        assert data["author"] == "New Author"

    async def test_library_admin_creates_book(
        self, test_db: AsyncSession, client: AsyncClient, library_admin: User
    ):
        headers = await make_auth_header(test_db, library_admin)
        payload = {
            "title": "Library Book",
            "author": "Library Author",
            "category": "history",
        }

        response = await client.post("/books", json=payload, headers=headers)

        data = response.json()

        assert response.status_code == 201
        assert data["title"] == "Library Book"
        assert data["author"] == "Library Author"

    async def test_receptionist_cannot_create_book(
        self, test_db: AsyncSession, client: AsyncClient, receptionist: User
    ):
        headers = await make_auth_header(test_db, receptionist)
        payload = {
            "title": "Forbidden Book",
            "author": "Forbidden Author",
            "category": "fiction",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 403

    async def test_member_cannot_create_book(
        self, test_db: AsyncSession, client: AsyncClient
    ):
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)
        payload = {
            "title": "Member Book",
            "author": "Member Author",
            "category": "fiction",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_create_book(self, client: AsyncClient):
        payload = {
            "title": "Anon Book",
            "author": "Anon Author",
            "category": "fiction",
        }

        response = await client.post("/books", json=payload)

        assert response.status_code == 401

    async def test_rejects_duplicate_title_and_author(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        await make_book(
            test_db, title="Duplicate", author="Same Author", created_by=system_admin.id
        )

        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "title": "Duplicate",
            "author": "Same Author",
            "category": "science",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 409

    async def test_same_title_different_author_is_allowed(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        await make_book(
            test_db, title="Same Title", author="Author A", created_by=system_admin.id
        )
        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "title": "Same Title",
            "author": "Author B",
            "category": "science",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 201

    async def test_rejects_invalid_input(
        self, test_db: AsyncSession, client: AsyncClient, system_admin: User
    ):
        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "title": "AB",
            "author": "CD",
            "category": "science",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 422

    async def test_rejects_future_publishing_date(
        self,
        client: AsyncClient,
        system_admin: User,
        test_db: AsyncSession,
    ):
        headers = await make_auth_header(test_db, system_admin)
        payload = {
            "title": "Future Book",
            "author": "Future Author",
            "category": "science",
            "publishing_date": "2099-01-01",
        }

        response = await client.post("/books", json=payload, headers=headers)

        assert response.status_code == 422


class TestGetBooks:
    async def test_public_access_returns_200(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books", headers=headers)

        assert response.status_code == 200

    async def test_returns_paginated_shape(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books", headers=headers)

        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data

    async def test_pagination_params_work(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        for _ in range(5):
            await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books?skip=0&limit=2", headers=headers)
        data = response.json()

        assert len(data["items"]) == 2
        assert data["has_more"] is True

    async def test_category_filter_works(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, category="fiction", created_by=system_admin.id)
        await make_book(test_db, category="fiction", created_by=system_admin.id)
        await make_book(test_db, category="science", created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books?category=fiction", headers=headers)
        data = response.json()

        assert data["total"] == 2
        assert all(b["category"] == "fiction" for b in data["items"])

    async def test_title_search_works(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, title="Django Unleashed", created_by=system_admin.id)
        await make_book(test_db, title="Flask Web Dev", created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books?title=django", headers=headers)
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["title"] == "Django Unleashed"

    async def test_sort_order_works(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, title="Zebra", created_by=system_admin.id)
        await make_book(test_db, title="Apple", created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books?sort_by=title&order=asc", headers=headers)
        data = response.json()

        titles = [b["title"] for b in data["items"]]
        assert titles == sorted(titles)

    async def test_empty_result_for_no_match(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/books?title=zzz_no_match_zzz", headers=headers)
        data = response.json()

        assert data["total"] == 0
        assert data["items"] == []


class TestGetBookByID:
    async def test_public_access_returns_200(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(f"/books/{book.id}", headers=headers)

        assert response.status_code == 200

    async def test_returns_correct_fields(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(f"/books/{book.id}", headers=headers)
        data = response.json()

        assert data["id"] == book.id
        assert data["title"] == book.title
        assert data["author"] == book.author
        assert data["category"] == book.category

    async def test_returns_404_for_unknown_id(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(f"/books/{book.id + 999999}", headers=headers)

        assert response.status_code == 404

    async def test_second_request_returns_same_data(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        headers = await make_auth_header(test_db, system_admin)

        r1 = await client.get(f"/books/{book.id}", headers=headers)
        r2 = await client.get(f"/books/{book.id}", headers=headers)

        assert r1.json() == r2.json()


class TestUpdateBook:
    async def test_system_admin_updates_book(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, system_admin)
        payload = {"title": "Updated Title"}

        response = await client.patch(
            f"/books/{book.id}", json=payload, headers=headers
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_library_admin_updates_book(
        self,
        client: AsyncClient,
        library_admin: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, library_admin)
        payload = {"author": "Updated Author"}

        response = await client.patch(
            f"/books/{book.id}", json=payload, headers=headers
        )

        assert response.status_code == 200
        assert response.json()["author"] == "Updated Author"

    async def test_receptionist_cannot_update_book(
        self,
        client: AsyncClient,
        receptionist: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, receptionist)
        payload = {"title": "Hacked Title"}

        response = await client.patch(
            f"/books/{book.id}", json=payload, headers=headers
        )

        assert response.status_code == 403

    async def test_unauthenticated_cannot_update_book(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        payload = {"title": "Anon Update"}

        response = await client.patch(f"/books/{book.id}", json=payload)

        assert response.status_code == 401

    async def test_returns_404_for_unknown_book(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, system_admin)
        payload = {"title": "Anything"}

        response = await client.patch(
            f"/books/{book.id + 999999}", json=payload, headers=headers
        )

        assert response.status_code == 404

    async def test_rejects_duplicate_title_author_on_update(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        await make_book(
            test_db, title="Existing", author="Author A", created_by=system_admin.id
        )
        book2 = await make_book(
            test_db, title="Other", author="Author B", created_by=system_admin.id
        )
        headers = await make_auth_header(test_db, system_admin)

        payload = {"title": "Existing", "author": "Author A"}

        response = await client.patch(
            f"/books/{book2.id}", json=payload, headers=headers
        )

        assert response.status_code == 409

    async def test_cache_invalidated_after_update(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, system_admin)

        await client.get(f"/books/{book.id}")

        await client.patch(
            f"/books/{book.id}", json={"title": "Cache Busted"}, headers=headers
        )

        response = await client.get(f"/books/{book.id}", headers=headers)
        assert response.json()["title"] == "Cache Busted"
