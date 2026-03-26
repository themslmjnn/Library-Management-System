from pydantic import BaseModel, Field

from typing import Optional
from datetime import date, datetime

from src.schemas.base_schema import BaseSchema


class LoanedBookBase(BaseModel):
    book_id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    due_at: date


class LoanedBookCreate(LoanedBookBase):
    pass


class LoanedBookResponse(LoanedBookBase, BaseSchema):
    id: int

    created_by: int = Field(ge=1)
    loaned_at: datetime
    returned_at: Optional[datetime] = None


class LoanedBookSearch(BaseModel):
    book_id: Optional[int] = None
    user_id: Optional[int] = None
    created_by: Optional[int] = None
    due_at: Optional[date] = None
    returned_at: Optional[date] = None


class LoanedBookUpdate(LoanedBookSearch):
    pass


class ReturnLoanResponse(LoanedBookResponse):
    pass