from pydantic import BaseModel, Field

from typing import Optional
from datetime import datetime

from src.schemas.base_schema import BaseSchema


class BookInventoryBase(BaseModel):
    book_id: int
    quantity_added: int


class BookInventoryCreate(BookInventoryBase):
    pass


class BookInventoryResponse1(BookInventoryBase, BaseSchema):
    id: int

    added_by: int
    added_at: datetime


class BookInventoryResponse2(BookInventoryResponse1):
    updated_at: datetime


class BookInventoryUpdate(BaseModel):
    book_id: Optional[int] = None
    quantity_added: Optional[int] = None
    added_by: Optional[int] = None


class BookInventoryUpdateResponse(BaseSchema):
    id: int

    added_by: int

    updated_at: datetime


class BookInventorySearch(BaseModel):
    book_id: Optional[int] = Field(None, ge=1)
    added_by: Optional[int] = Field(None, ge=1)
    quantity_added: Optional[int] = Field(None, ge=1)