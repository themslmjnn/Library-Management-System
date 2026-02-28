from pydantic import BaseModel, Field

from typing import Optional
from datetime import datetime

class BookInventoryBase(BaseModel):
    book_id: int
    added_by: int
    quantity_added: int


class BookInventoryCreate(BookInventoryBase):
    pass


class BookInventoryResponse(BookInventoryBase):
    pass


class BookInventorySearch(BaseModel):
    book_id: Optional[int] = Field(None, ge=1)
    added_by: Optional[int] = Field(None, ge=1)
    added_at: Optional[datetime] = None
    quantity_added: Optional[int] = Field(None, ge=1)