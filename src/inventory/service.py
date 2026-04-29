from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import delete_cache, get_cache, set_cache
from src.core.logging import get_logger
from src.inventory.models import Inventory
from src.inventory.repository import InventoryRepository
from src.inventory.schemas import CreateInventory, InventoryResponse, SearchInventory
from src.pagination import PaginatedResponse
from src.utils.cache_keys import inventory_detail_key
from src.utils.exception_constants import HTTP404
from src.utils.exceptions import InventoryNotFoundError, check_book_id_fkey_error
from src.utils.helpers import ensure_exists

logger = get_logger(__name__)


class InventoryService:    
    @staticmethod
    async def add_inventory(db: AsyncSession, user_id: int, inventory_request: CreateInventory) -> Inventory:
        if inventory_request.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity can not be less than or equal to 0",
            )
        
        new_inventory = Inventory(
            **inventory_request.model_dump(),
            added_by=user_id,
        )

        try:
            InventoryRepository.add_inventory(db, new_inventory)

            await db.commit()
            await db.refresh(new_inventory)

            logger.info(
                "inventory_added",
                inventory_id=new_inventory.id,
                added_by=user_id,
            )

            return new_inventory
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "create_inventory_failed",
                requested_by=user_id,
                error=str(e.orig),
            )

            check_book_id_fkey_error(e)
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
    async def get_inventory_by_id(db: AsyncSession, inventory_id: int) -> InventoryResponse:
        cached = await get_cache(inventory_detail_key(inventory_id))
        if cached is not None:
            return cached
        
        inventory = await InventoryRepository.get_inventory_by_id(db, inventory_id)
        ensure_exists(inventory, InventoryNotFoundError(HTTP404.INVENTORY))

        serialized = InventoryResponse.model_validate(inventory).model_dump(mode="json")
        await set_cache(inventory_detail_key(inventory_id), serialized, 120)
        
        return serialized
    
    
    @staticmethod
    async def update_inventory(db: AsyncSession, user_id: int, quantity: int, inventory_id: int) -> Inventory:
        inventory = await InventoryRepository.get_inventory_by_id(db, inventory_id)
        ensure_exists(inventory, InventoryNotFoundError(HTTP404.INVENTORY))
        
        inventory.quantity = quantity

        await db.commit()

        key = inventory_detail_key(inventory_id)
        await delete_cache(key)

        logger.info(
            "inventory_updated",
            inventory_id=inventory.id,
            requested_by=user_id,
        )

        return inventory