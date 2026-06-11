from pydantic import BaseModel, EmailStr, Field, field_validator

from src.utils.enums import UserRole
from src.utils.validators import validate_password, validate_phone_number


class CreateAccessTokenRequest(BaseModel):
    user_id: int
    role: UserRole
    access_token_version: int


class CreateRefreshTokenRequest(BaseModel):
    user_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ActivateAccountWithToken(BaseModel):
    email: EmailStr
    invite_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return validate_password(field)


class ActivateAccountWithCode(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordRequest(BaseModel):
    identifier: EmailStr
    reset_token: str
    new_password: str


class ForgotPasswordPublicRequest(BaseModel):
    username: str = Field(min_length=6, max_length=20)
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, field: str) -> str:
        return validate_phone_number(field)
