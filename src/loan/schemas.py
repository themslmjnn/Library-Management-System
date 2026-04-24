from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.utils.base_schema import BaseSchema


class LoanBase(BaseModel):
    book_id: int = Field(ge=1)
    user_id: int = Field(ge=1)
    due_at: date


class CreateLoanPublic(BaseModel):
    book_id: int = Field(ge=1)
    due_at: date


class LoanResponse(LoanBase, BaseSchema):
    id: int
    created_by: int
    loaned_at: datetime
    returned_at: datetime | None = None


class SearchLoan(BaseModel):
    book_id: Optional[int] = None
    user_id: Optional[int] = None
    created_by: Optional[int] = None
    due_at: Optional[date] = None
    returned_at: Optional[date] = None

class SearchLoanPublic(BaseModel):
    book_id: Optional[int] = None
    due_at: Optional[date] = None
    returned_at: Optional[date] = None


class UpdateLoan(BaseModel):
    book_id: Optional[int] = None
    user_id: Optional[int] = None
    due_at: Optional[date] = None