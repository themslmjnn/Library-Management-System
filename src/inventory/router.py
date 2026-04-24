from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_roles,
)
from src.inventory.schemas import (
    CreateInventory,
    InventoryResponse,
    SearchInventory,
)
from src.inventory.service import InventoryService
from src.pagination import PaginatedResponse
from src.user.models import User, UserRole
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/inventories",
    tags=["Inventories"],
)


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory(
        db: async_db_dependency, 
        current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
        inventory_request: CreateInventory):

    return await InventoryService.add_inventory(db, current_user, inventory_request)


@router.get("", response_model=PaginatedResponse[InventoryResponse], status_code=status.HTTP_200_OK)
async def get_inventories(
        db: async_db_dependency,
        pagination: pagination_dependency,
        _: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
        filters: Annotated[SearchInventory, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await InventoryService.get_inventories(
        db, 
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order
    )
    

@router.put("/{inventory_id}", response_model=InventoryResponse, status_code=status.HTTP_200_OK)
async def update_inventory(
        db: async_db_dependency, 
        current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
        quantity: int, 
        inventory_id: path_param_int_ge1):

    return await InventoryService.update_inventory(db, current_user, quantity, inventory_id)


@router.get("/{inventory_id}", response_model=InventoryResponse, status_code=status.HTTP_200_OK)
async def get_inventory_by_id(
        db: async_db_dependency, 
        _: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin))],
        inventory_id: path_param_int_ge1):

    return await InventoryService.get_inventory_by_id(db, inventory_id)