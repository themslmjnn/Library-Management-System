from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from src.book.models import BookCategory
from src.utils.base_schema import BaseSchema
from src.utils.validators import validate_publishing_date


class BookBase(BaseModel):
    title: str = Field(min_length=3, max_length=50)
    author: str = Field(min_length=3, max_length=50)
    category: BookCategory
    description: str | None = Field(max_length=100, default=None)
    publishing_date: date | None = None


class CreateBook(BookBase):
    @field_validator("publishing_date")
    @classmethod
    def validate_publishing_date(cls, field: date) -> date:
        return validate_publishing_date(field)


class BookResponse(BookBase, BaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime


class UpdateBook(BaseModel):
    title: str | None = Field(min_length=3, max_length=50, default=None)
    author: str | None = Field(min_length=3, max_length=50, default=None)
    category: BookCategory | None = None
    description: str | None = Field(max_length=100, default=None)
    publishing_date: date | None = None

    @field_validator("publishing_date")
    @classmethod
    def validate_publishing_date(cls, field: date) -> date:
        return validate_publishing_date(field)


class SearchBook(BaseModel):
    title: str | None = None
    author: str | None = None
    category: BookCategory | None = None
    publishing_date: date | None = None