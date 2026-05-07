import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.inventory.schemas import CreateInventory, SearchInventory
from src.inventory.service import InventoryService
from src.user.models import User
from src.utils.exceptions import BookNotFoundError, InventoryNotFoundError
from tests.conftest import make_auth_header
from tests.factories import make_book, make_library_admin, make_member, make_system_admin


class TestAddInventory:
    async def test_adds_inventory_successfully(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        request = CreateInventory(book_id=book.id, quantity=5)
        inventory = await InventoryService.add_inventory(test_db, system_admin.id, request)

        assert inventory.id is not None
        assert inventory.book_id == book.id
        assert inventory.quantity == 5
        assert inventory.added_by == system_admin.id


    async def test_rejects_zero_quantity(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        request = CreateInventory(book_id=book.id, quantity=0)

        with pytest.raises(Exception) as exc_info:
            await InventoryService.add_inventory(test_db, system_admin.id, request)

        assert exc_info.value.status_code == 400


    async def test_rejects_negative_quantity(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        request = CreateInventory(book_id=book.id, quantity=-1)

        with pytest.raises(Exception) as exc_info:
            await InventoryService.add_inventory(test_db, system_admin.id, request)

        assert exc_info.value.status_code == 400


    async def test_rejects_invalid_book_id(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        non_existent_book_id = book.id + 999999

        request = CreateInventory(book_id=non_existent_book_id, quantity=5)

        with pytest.raises(BookNotFoundError):
            await InventoryService.add_inventory(test_db, system_admin.id, request)


    async def test_multiple_inventory_records_for_same_book(
        self, test_db: AsyncSession, system_admin: User
    ):
        book = await make_book(test_db, created_by=system_admin.id)

        r1 = CreateInventory(book_id=book.id, quantity=3)
        r2 = CreateInventory(book_id=book.id, quantity=5)

        inv1 = await InventoryService.add_inventory(test_db, system_admin.id, r1)
        inv2 = await InventoryService.add_inventory(test_db, system_admin.id, r2)

        assert inv1.id != inv2.id
        assert inv1.quantity == 3
        assert inv2.quantity == 5


class TestGetInventoryById:
    async def test_returns_correct_inventory(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        request = CreateInventory(book_id=book.id, quantity=10)
        inventory = await InventoryService.add_inventory(test_db, system_admin.id, request)

        result = await InventoryService.get_inventory_by_id(test_db, inventory.id)

        assert result["id"] == inventory.id
        assert result["book_id"] == book.id
        assert result["quantity"] == 10
        assert result["added_by"] == system_admin.id


    async def test_raises_for_unknown_id(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )
        non_existent_id = inventory.id + 999999

        with pytest.raises(InventoryNotFoundError):
            await InventoryService.get_inventory_by_id(test_db, non_existent_id)


    async def test_second_call_returns_cached_result(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=7)
        )

        result1 = await InventoryService.get_inventory_by_id(test_db, inventory.id)
        result2 = await InventoryService.get_inventory_by_id(test_db, inventory.id)

        assert result1 == result2


    async def test_cache_invalidated_after_update(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )

        # populate cache
        await InventoryService.get_inventory_by_id(test_db, inventory.id)

        # update
        await InventoryService.update_inventory(test_db, system_admin.id, 99, inventory.id)

        # must return updated data
        result = await InventoryService.get_inventory_by_id(test_db, inventory.id)
        assert result["quantity"] == 99


class TestGetInventories:
    async def test_returns_paginated_response(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        for _ in range(3):
            await InventoryService.add_inventory(
                test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=1)
            )

        result = await InventoryService.get_inventories(
            test_db,
            skip=0,
            limit=20,
            filters=SearchInventory(),
            sort_by="added_at",
            order="desc",
        )

        assert "items" in result.model_dump()
        assert "total" in result.model_dump()
        assert result.total >= 3


    async def test_pagination_limit_works(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)

        for _ in range(5):
            await InventoryService.add_inventory(
                test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=1)
            )

        result = await InventoryService.get_inventories(
            test_db,
            skip=0,
            limit=2,
            filters=SearchInventory(),
            sort_by="added_at",
            order="desc",
        )

        assert len(result.items) == 2
        assert result.has_more is True


    async def test_filters_by_book_id(self, test_db: AsyncSession, system_admin: User):
        book1 = await make_book(test_db, created_by=system_admin.id)
        book2 = await make_book(test_db, created_by=system_admin.id)

        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book1.id, quantity=3)
        )
        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book2.id, quantity=5)
        )

        result = await InventoryService.get_inventories(
            test_db,
            skip=0,
            limit=20,
            filters=SearchInventory(book_id=book1.id),
            sort_by="added_at",
            order="desc",
        )

        assert result.total == 1
        assert result.items[0].book_id == book1.id


    async def test_filters_by_added_by(self, test_db: AsyncSession, system_admin: User):
        library_admin = await make_library_admin(test_db)
        book = await make_book(test_db, created_by=system_admin.id)

        await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=3)
        )
        await InventoryService.add_inventory(
            test_db, library_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )

        result = await InventoryService.get_inventories(
            test_db,
            skip=0,
            limit=20,
            filters=SearchInventory(added_by=system_admin.id),
            sort_by="added_at",
            order="desc",
        )

        assert result.total == 1
        assert result.items[0].added_by == system_admin.id


    async def test_empty_result_when_no_match(self, test_db: AsyncSession, system_admin: User):
        book = await make_book(test_db, created_by=system_admin.id)
        inventory = await InventoryService.add_inventory(
            test_db, system_admin.id, CreateInventory(book_id=book.id, quantity=5)
        )

        result = await InventoryService.get_inventories(
            test_db,
            skip=0,
            limit=20,
            filters=SearchInventory(book_id=inventory.book_id + 999999),
            sort_by="added_at",
            order="desc",
        )

        assert result.total == 0
        assert result.items == []