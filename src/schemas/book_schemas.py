from pydantic import BaseModel, Field

from typing import Optional
from datetime import date


class BookBase(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    author: str = Field(min_length=3, max_length=50)
    category: str = Field(min_length=3, max_length=30)
    description: Optional[str] = Field(None, max_length=100)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = Field(None)


class BookCreatePublic(BookBase):
    pass


class BookCreateAdmin(BookBase):
    created_by: int = Field(ge=1)


class BookResponse(BookBase):
    id: int

    class Config:
        from_attributes = True


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=50)
    author: Optional[str] = Field(None, min_length=3, max_length=50)
    category: Optional[str] = Field(None, min_length=3, max_length=30)
    description: Optional[str] = Field(None, max_length=100)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = Field(None)


class BookSearch(BaseModel):
    title: Optional[str] = Field(None, min_length=3)
    author: Optional[str] = Field(None, min_length=3)
    category: Optional[str] = Field(None, min_length=3)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = Field(None)