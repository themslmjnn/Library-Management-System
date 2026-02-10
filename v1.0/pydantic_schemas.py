from pydantic import BaseModel, Field, EmailStr
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

class UserBase(BaseModel):
    username: str = Field(min_length=6, max_length=20)
    first_name: str = Field(min_length=2, max_length=20)
    last_name: str = Field(min_length=2, max_length=20)
    date_of_birth: date
    email_address: EmailStr

class UserCreate(UserBase):
    hash_password: str = Field(min_length=6)
    role: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=True)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True
