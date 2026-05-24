from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.inventory.schemas import CreateInventory
from src.inventory.service import InventoryService
from src.users.models import User
from tests.conftest import make_auth_header
from tests.factories import (
    make_book,
    make_member,
)


class TestAddInventory:
    async def test_system_admin_adds_inventory(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, system_admin)
        payload = {"book_id": book.id, "quantity": 5}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["book_id"] == book.id
        assert data["quantity"] == 5
        assert data["added_by"] == system_admin.id

    async def test_library_admin_adds_inventory(
        self,
        client: AsyncClient,
        library_admin: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, library_admin)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 201

    async def test_receptionist_cannot_add_inventory(
        self,
        client: AsyncClient,
        receptionist: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        headers = await make_auth_header(test_db, receptionist)
        payload = {"book_id": book.id, "quantity": 3}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 403

    async def test_member_cannot_add_inventory(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        member = await make_member(test_db)
        headers = await make_auth_header(test_db, member)
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
        headers = await make_auth_header(test_db, system_admin)
        payload = {"book_id": book.id + 999999, "quantity": 5}

        response = await client.post("/inventories", json=payload, headers=headers)

        assert response.status_code == 404


class TestGetInventories:
    async def test_system_admin_gets_inventories(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get("/inventories", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_library_admin_gets_inventories(
        self,
        client: AsyncClient,
        library_admin: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, library_admin)

        response = await client.get("/inventories", headers=headers)

        assert response.status_code == 200

    async def test_receptionist_cannot_get_inventories(
        self, client: AsyncClient, receptionist: User, test_db: AsyncSession
    ):
        headers = await make_auth_header(test_db, receptionist)

        response = await client.get("/inventories", headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_get_inventories(self, client: AsyncClient):
        response = await client.get("/inventories")

        assert response.status_code == 401

    async def test_pagination_works(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        for _ in range(5):
            await InventoryService.add_inventory(
                test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=1)
            )

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get("/inventories?skip=0&limit=2", headers=headers)

        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True

    async def test_filter_by_book_id_works(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book1 = await make_book(test_db, created_by=system_admin.id)
        book2 = await make_book(test_db, created_by=system_admin.id)

        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book1.id, quantity=3)
        )
        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book2.id, quantity=5)
        )

        headers = await make_auth_header(test_db, system_admin)
        response = await client.get(f"/inventories?book_id={book1.id}", headers=headers)

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["book_id"] == book1.id


class TestGetInventoryById:
    async def test_returns_correct_inventory(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=7)
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(f"/inventories/{inventory.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == inventory.id
        assert data["book_id"] == book.id
        assert data["quantity"] == 7

    async def test_returns_404_for_unknown_id(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.get(
            f"/inventories/{inventory.id + 999999}", headers=headers
        )

        assert response.status_code == 404

    async def test_receptionist_cannot_get_by_id(
        self,
        client: AsyncClient,
        receptionist: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, receptionist)

        response = await client.get(f"/inventories/{inventory.id}", headers=headers)

        assert response.status_code == 403

    async def test_unauthenticated_cannot_get_by_id(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )

        response = await client.get(f"/inventories/{inventory.id}")

        assert response.status_code == 401

    async def test_second_request_returns_same_data(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        r1 = await client.get(f"/inventories/{inventory.id}", headers=headers)
        r2 = await client.get(f"/inventories/{inventory.id}", headers=headers)

        assert r1.json() == r2.json()


class TestUpdateInventory:
    async def test_system_admin_updates_inventory(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/inventories/{inventory.id}",
            json={"quantity": 20},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 20

    async def test_library_admin_updates_inventory(
        self,
        client: AsyncClient,
        library_admin: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, library_admin)

        response = await client.patch(
            f"/inventories/{inventory.id}",
            json={"quantity": 10},
            headers=headers,
        )

        assert response.status_code == 200

    async def test_receptionist_cannot_update_inventory(
        self,
        client: AsyncClient,
        receptionist: User,
        test_db: AsyncSession,
        system_admin: User,
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, receptionist)

        response = await client.patch(
            f"/inventories/{inventory.id}",
            json={"quantity": 10},
            headers=headers,
        )

        assert response.status_code == 403

    async def test_unauthenticated_cannot_update_inventory(
        self, client: AsyncClient, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )

        response = await client.patch(
            f"/inventories/{inventory.id}",
            json={"quantity": 10},
        )

        assert response.status_code == 401

    async def test_returns_404_for_unknown_id(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        response = await client.patch(
            f"/inventories/{inventory.id + 999999}",
            json={"quantity": 10},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_cache_invalidated_after_update(
        self, client: AsyncClient, system_admin: User, test_db: AsyncSession
    ):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        headers = await make_auth_header(test_db, system_admin)

        await client.get(f"/inventories/{inventory.id}", headers=headers)

        await client.patch(
            f"/inventories/{inventory.id}",
            json={"quantity": 77},
            headers=headers,
        )

        response = await client.get(f"/inventories/{inventory.id}", headers=headers)
        assert response.json()["quantity"] == 77
