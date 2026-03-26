from pydantic import BaseModel, Field, field_validator

from typing import Optional
from datetime import date, datetime

from src.models.book_model import Category
from src.schemas.base_schema import BaseSchema
from src.utils.schema_fields_validator import _validate_publishing_date


class BookBase(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    author: str = Field(min_length=3, max_length=50)
    category: Category
    description: Optional[str] = Field(None, max_length=100)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = None


class BookCreate(BookBase):
    @field_validator("publishing_date")
    @classmethod
    def validate_publishing_date(cls, v: date) -> date:
        return _validate_publishing_date(v)


class BookResponse1(BookBase, BaseSchema):
    id: int

    created_at: datetime


class BookResponse2(BookResponse1):
    updated_at: datetime


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=50)
    author: Optional[str] = Field(None, min_length=3, max_length=50)
    category: Optional[Category] = None
    description: Optional[str] = Field(None, max_length=100)
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = None

    @field_validator("publishing_date")
    @classmethod
    def validate_publishing_date(cls, v: date) -> date:
        return _validate_publishing_date(v)


class BookUpdateResponse(BookBase, BaseSchema):
    id: int

    updated_at: datetime


class BookSearch(BaseModel):
    title: Optional[str] = Field(None, min_length=3)
    author: Optional[str] = Field(None, min_length=3)
    category: Optional[Category] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    publishing_date: Optional[date] = None