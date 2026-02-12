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

class BookUpdate(BaseModel):
    title: Optional[str] = Field(min_length=3, max_length=50, default=None)
    author: Optional[str] = Field(min_length=3, max_length=50, default=None)
    category: Optional[str] = Field(min_length=3, max_length=30, default=None)
    description: Optional[str] = Field(default=None, max_length=100)
    rating: Optional[float] = Field(default=None, ge=1, le=5)
    publishing_date: Optional[date] = Field(default=None)

class UserBase(BaseModel):
    username: str = Field(min_length=6, max_length=20)
    first_name: str = Field(min_length=2, max_length=20)
    last_name: str = Field(min_length=2, max_length=20)
    date_of_birth: date
    email_address: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=6)
    role: str = Field(default="User")
    is_active: bool = Field(default=True)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = Field(min_length=6, max_length=20, default=None)
    first_name: Optional[str] = Field(min_length=2, max_length=20, default=None)
    last_name: Optional[str] = Field(min_length=2, max_length=20, default=None)
    date_of_birth: Optional[date] = Field(default=None)
    email_address: Optional[EmailStr] = Field(default=None)


class UserUpdatePassword(BaseModel):
    email_address: EmailStr
    old_password: str = Field(min_length=6)
    new_password: str = Field(min_length=6)
