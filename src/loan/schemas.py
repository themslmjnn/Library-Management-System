from datetime import date, datetime

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
    inventory_id: int
    created_by: int
    loaned_at: datetime
    returned_at: datetime | None = None


class SearchLoan(BaseModel):
    book_id: int | None = None
    user_id: int | None = None
    created_by: int | None = None
    due_at: date | None = None
    returned_at: date | None = None

class SearchLoanPublic(BaseModel):
    book_id: int | None = None
    due_at: date | None = None
    returned_at: date | None = None


class UpdateLoan(BaseModel):
    book_id: int | None = None
    user_id: int | None = None
    due_at: date | None = None