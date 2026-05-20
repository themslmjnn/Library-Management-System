from datetime import datetime

from pydantic import BaseModel, Field

from src.utils.base_schema import BaseSchema


class InventoryBase(BaseModel):
    book_id: int = Field(ge=1)
    quantity: int = Field(ge=1)


class CreateInventory(InventoryBase):
    pass


class InventoryResponse(InventoryBase, BaseSchema):
    id: int
    added_by: int
    created_at: datetime
    updated_at: datetime

class UpdateInventoryRequest(BaseModel):
    quantity: int = Field(ge=0)

class SearchInventory(BaseModel):
    book_id: int | None = Field(ge=1, default=None)
    added_by: int | None = Field(ge=1, default=None)
    quantity: int | None = Field(ge=1, default=None)
