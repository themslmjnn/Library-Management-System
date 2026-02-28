# Imports
from pydantic import BaseModel, Field

from typing import Optional
from datetime import date, datetime


# Schemas
class LoanBookBase(BaseModel):
    user_id: int = Field(ge=1)
    book_id: int = Field(ge=1)
    due_at: date


class LoanBookCreatePublic(LoanBookBase):
    pass


class LoanBookCreateMember(LoanBookBase):
    created_by: int = Field(ge=1)


class LoanBookCreateAdmin(LoanBookCreateMember):
    pass


class LoanBookRepsonse(LoanBookBase):
    id: int

    class Config:
        from_attributes = True


class LoanBookSearch(BaseModel):
    user_id: Optional[int] = None
    book_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    due_at: Optional[date] = None

class ReturnLoanRequest(LoanBookBase):
    pass

class ReturnLoanResponse(LoanBookCreateMember):
    returned_at: datetime
