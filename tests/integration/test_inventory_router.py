import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.user.models import User, UserRole
from src.inventory.schemas import CreateInventory
from tests.factories import make_book, make_member, make_receptionist, make_library_admin
from tests.conftest import make_auth_header


class TestAddInventory:
    async def test_system_admin_adds_inventory(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(system_admin)
        payload = {"book_id": book.id, "quantity": 5}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == book.id
        assert data["quantity"] == 5
        assert data["added_by"] == system_admin.id

    async def test_library_admin_adds_inventory(
        self, client: AsyncClient, library_admin: User, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(library_admin)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 201

    async def test_receptionist_cannot_add_inventory(
        self, client: AsyncClient, receptionist: User, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(receptionist)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 403

    async def test_member_cannot_add_inventory(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        member = await make_member(test_db)
        headers = make_auth_header(member)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_add_inventory(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload)

        assert response.status_code == 401

    async def test_rejects_invalid_book_id(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(system_admin)
        payload = {"book_id": book.id + 999999, "quantity": 5}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 404

    async def test_rejects_zero_quantity(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(system_admin)
        payload = {"book_id": book.id, "quantity": 0}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 400

    async def test_rejects_negative_quantity(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = make_auth_header(system_admin)
        payload = {"book_id": book.id, "quantity": -3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 400