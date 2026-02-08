from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class BookBase(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    author: str = Field(min_length=3, max_length=50)
    category: str = Field(min_length=3, max_length=30)
    description: Optional[str] = Field(default=None, max_length=100)
    rating: Optional[float] = Field(default=None, ge=1, le=5)
    publishing_date: date

class BookCreate(BookBase):
    pass

class BookResponse(BookBase):
    id: int

    class Config:
        from_attributes = True

