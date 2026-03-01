# Imports
from pydantic import BaseModel, Field

from typing import Optional
from datetime import date, datetime


# Schemas
class LoanBookBase(BaseModel):
    book_id: int = Field(ge=1)
    user_id: int = Field(ge=1)


class LoanBookCreate(LoanBookBase):
    due_at: date


class LoanBookResponse(BaseModel):
    id: int
    book_id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    created_by: int = Field(ge=1)
    loaned_at: datetime
    due_at: date
    returned_at: Optional[datetime] = Field(None)

    class Config:
        from_attributes = True


class LoanBookSearch(BaseModel):
    book_id: Optional[int] = None
    user_id: Optional[int] = None
    created_by: Optional[int] = None
    loaned_at: Optional[datetime] = None
    due_at: Optional[date] = None


class ReturnLoanRequest(LoanBookBase):
    due_at: date


class ReturnLoanResponse(LoanBookCreate):
    returned_at: datetime
