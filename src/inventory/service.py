from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.inventory.models import Inventory
from src.inventory.repository import InventoryRepository
from src.inventory.schemas import CreateInventory, SearchInventory
from src.pagination import PaginatedResponse
from src.user.models import User
from src.utils.exception_constants import HTTP404
from src.utils.exceptions import check_added_by_fkey_error, check_book_id_fkey_error
from src.utils.helpers import ensure_exists

logger = get_logger(__name__)


class InventoryService:    
    @staticmethod
    async def add_inventory(db: AsyncSession, current_user: User, inventory_request: CreateInventory) -> Inventory:
        new_inventory = Inventory(
            book_id=inventory_request.book_id,
            added_by=current_user.id,
            quantity_added=inventory_request.quantity_added
        )

        try:
            InventoryRepository.add_inventory(db, new_inventory)

            await db.commit()
            await db.refresh(new_inventory)

            logger.info(
                "inventory_added",
                inventory_id=new_inventory.id,
                added_by=current_user.id,
            )

            return new_inventory
        
        except IntegrityError as e:
            logger.error(
                "inventory_creation_failed",
                requested_by=current_user.id,
                error=str(e.orig),
            )
            check_book_id_fkey_error(e)
            check_added_by_fkey_error(e)
            raise

    
    @staticmethod
    async def get_inventories(
        db: AsyncSession, 
        skip: int,
        limit: int,
        filters: SearchInventory,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        inventories, total = await InventoryRepository.get_inventories(db, skip, limit, filters, sort_by, order)
        return PaginatedResponse(
            items=inventories,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    

    @staticmethod
    async def get_inventory_by_id(db: AsyncSession, inventory_id: int) -> Inventory:
        inventory = await InventoryRepository.get_inventory_by_id(db, inventory_id)

        ensure_exists(inventory, HTTP404.INVENTORY)
        
        return inventory
    
    
    @staticmethod
    async def update_inventory(db: AsyncSession, current_user: User, quantity: int, inventory_id: int) -> Inventory:
        inventory = await InventoryRepository.get_inventory_by_id(db, inventory_id)

        ensure_exists(inventory, HTTP404.INVENTORY)
        
        inventory.quantity_added = quantity

        await db.commit()

        logger.info(
            "inventory_updated",
            inventory_id=inventory.id,
            requested_by=current_user.id
        )
        return inventory