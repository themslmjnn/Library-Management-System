from pydantic import BaseModel, Field

from datetime import date, datetime


class BookLoaningBase(BaseModel):
    user_id: int = Field(ge=1)
    book_id: int = Field(ge=1)
    created_by: str
    created_at: datetime
    due_at: date


class BookLoaningCreate(BookLoaningBase):
    pass


class BookLoaningResponse(BookLoaningBase):
    id: int

    class Config:
        from_attributes = True