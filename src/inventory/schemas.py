from datetime import datetime

from pydantic import BaseModel, Field

from src.utils.base_schema import BaseSchema


class InventoryBase(BaseModel):
    book_id: int
    quantity: int


class CreateInventory(InventoryBase):
    pass


class InventoryResponse(InventoryBase, BaseSchema):
    id: int
    added_by: int
    added_at: datetime
    updated_at: datetime


class UpdateInventory(BaseModel):
    book_id: int | None = None
    quantity: int | None = None
    added_by: int | None = None


class SearchInventory(BaseModel):
    book_id: int | None = Field(ge=1, default=None)
    added_by: int | None = Field(ge=1, default=None)
    quantity: int | None = Field(ge=1, default=None)