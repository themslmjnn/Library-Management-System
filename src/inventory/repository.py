from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.inventory.models import Inventory
from src.inventory.schemas import CreateInventory, SearchInventory

ALLOWED_SORT_FIELDS_INVENTORY = {"created_at", "book_id", "added_by"}


class InventoryRepository:    
    @staticmethod
    def add_inventory(db: AsyncSession, new_inventory: CreateInventory) -> None:
        db.add(new_inventory)


    @staticmethod
    async def get_inventories(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchInventory | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Inventory], int]:
        
        base_query = select(Inventory)

        if filters:
            if filters.book_id is not None:
                base_query = base_query.filter(Inventory.book_id == filters.book_id)

            if filters.added_by is not None:
                base_query = base_query.filter(Inventory.added_by == filters.added_by)

            if filters.quantity is not None:
                base_query = base_query.filter(Inventory.quantity == filters.quantity)

        if sort_by not in ALLOWED_SORT_FIELDS_INVENTORY:
            sort_by = "created_at"

        sort_column = getattr(Inventory, sort_by, Inventory.added_at)

        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total

    
    @staticmethod
    async def get_inventory_by_id(db: AsyncSession, inventory_id: int) -> Inventory | None:
        query = (
            select(Inventory)
            .filter(Inventory.id == inventory_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()

    
    @staticmethod
    async def get_available_inventories(db: AsyncSession, book_id: int) -> list[Inventory]:
        query = (
            select(Inventory)
            .filter(and_(
                Inventory.quantity != 0,
                Inventory.book_id == book_id,
                )
            )
            .order_by(Inventory.added_at.asc())
        )

        result = await db.execute(query)

        return result.scalars().all()