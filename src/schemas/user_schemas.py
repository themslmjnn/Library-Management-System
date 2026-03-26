from pydantic import BaseModel, Field, EmailStr, field_validator

from typing import Optional
from datetime import date, datetime

from src.models.user_model import UserRole
from src.schemas.base_schema import BaseSchema
from src.utils.schema_fields_validator import _validate_date_of_birth, _validate_email_address, _validate_password


class UserBase(BaseModel):
    username: str = Field(min_length=6, max_length=20)
    first_name: str = Field(min_length=2, max_length=20)
    last_name: str = Field(min_length=2, max_length=20)
    date_of_birth: date
    email_address: EmailStr


    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, field: date) -> date:
        return _validate_date_of_birth(field)
    
    @field_validator("email_address")
    @classmethod
    def valdiate_email_address(cls, field: str) -> str:
        return _validate_email_address(field)


class UserCreatePublic(UserBase):
    password: str = Field(min_length=8)


    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return _validate_password(field)
    

class UserResponsePublic1(UserBase, BaseSchema):
    id: int

    created_at: datetime


class UserResponsePublic2(UserResponsePublic1):
    updated_at: datetime


class UserCreateAdmin(UserBase):
    password: str = Field(min_length=8)

    role: UserRole


    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return _validate_password(field)


class UserResponseAdmin1(UserBase, BaseSchema):
    id: int

    role: UserRole
    is_active: bool

    created_at: datetime


class UserResponseAdmin2(UserResponseAdmin1):
    updated_at: datetime


class UserUpdateBase(BaseModel):
    username: Optional[str] = Field(None, min_length=6, max_length=20)
    first_name: Optional[str] = Field(None, min_length=2, max_length=20)
    last_name: Optional[str] = Field(None, min_length=2, max_length=20)
    date_of_birth: Optional[date] = None
    email_address: Optional[EmailStr] = None


    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, field: date) -> date:
        return _validate_date_of_birth(field)
    
    @field_validator("email_address")
    @classmethod
    def valdiate_email_address(cls, field: str) -> str:
        return _validate_email_address(field)


class UserUpdatePublic(UserUpdateBase):
    pass


class UserUpdateAdmin(UserUpdateBase):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserUpdateResponsePublic(UserBase, BaseSchema):
    id: int

    updated_at: datetime


class UserUpdateResponseAdmin(UserBase, BaseSchema):
    id: int

    role: UserRole
    is_active: bool

    updated_at: datetime


class UserUpdatePasswordPublic(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password(v)


class UserUpdatePasswordAdmin(BaseModel):
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        return _validate_password(v)


class UserSearch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    date_of_birth: Optional[date] = None

    role: Optional[UserRole] = None
    
    is_active: Optional[bool] = None


class UserActivateAccountPublic(BaseModel):
    username: str
    password: str

class CurrentUserResponse(BaseSchema):
   id: int

   username: str = Field(min_length=6, max_length=20)

   role: UserRole