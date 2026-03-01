from pydantic import BaseModel, Field

from typing import Optional
from datetime import date

from src.models.book_model import Category


class BookBase(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    author: str = Field(min_length=3, max_length=50)
    category: Category = Field(min_length=3, max_length=30)
    description: Optional[str] = Field(None, max_length=100)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = Field(None)


class BookCreateAdmin(BookBase):
    pass


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
    category: Optional[Category] = Field(None, min_length=3)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = Field(None)