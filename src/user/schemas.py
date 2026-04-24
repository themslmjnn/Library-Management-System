from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.user.models import UserRole
from src.utils.base_schema import BaseSchema
from src.utils.validators import (
    validate_date_of_birth,
    validate_email,
    validate_password,
)


class CreateUserBase(BaseModel):
    username: str | None = Field(min_length=6, max_length=20, default=None)
    first_name: str = Field(min_length=2, max_length=20)
    last_name: str = Field(min_length=2, max_length=20)
    date_of_birth: date
    email: EmailStr
    phone_number: str = Field(min_length=10, max_length=20)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, field: date) -> date:
        return validate_date_of_birth(field)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, field: str) -> str:
        return validate_email(field)

class CreateUserAdmin(CreateUserBase):
    role: UserRole


class CreateUserPublic(CreateUserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return validate_password(field)
    

class UserResponseBase(BaseSchema):
    id: int
    username: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    email: EmailStr
    phone_number: str
    created_at: datetime
    updated_at: datetime

class UserResponseAdmin(UserResponseBase):
    role: UserRole
    is_active: bool
    created_by: int | None = None

class UserResponseStaff(UserResponseBase):
    role: UserRole


class UpdateUserBase(BaseModel):
    username: str | None = Field(min_length=6, max_length=20, default=None)
    first_name: str | None = Field(min_length=2, max_length=20, default=None)
    last_name: str | None = Field(min_length=2, max_length=20, default=None)
    date_of_birth: date | None = None
    email: EmailStr | None = None
    phone_number: str | None = Field(min_length=10, max_length=20, default=None)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, field: date) -> date:
        return validate_date_of_birth(field)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, field: str) -> str:
        return validate_email(field)

class UpdateUserAdmin(UpdateUserBase):
    role: UserRole | None = None
    is_active: bool | None = None


class UpdateUserPasswordAdmin(BaseModel):
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return validate_password(field)
    
class UpdateUserPasswordPublic(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return validate_password(field)


class SearchUserBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date| None = None
    email: str | None = None
    phone_number: str | None = None

class SearchUserAdmin(SearchUserBase):
    username: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None