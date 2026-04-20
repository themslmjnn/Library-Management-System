from pydantic import BaseModel, field_validator

from src.user.models import UserRole
from src.utils.validators import validate_password


class CreateAccessTokenRequest(BaseModel):
    user_id: int
    role: UserRole
    access_token_version: int

class CreateRefreshTokenRequest(BaseModel):
    user_id: int
    family: str


class LoginRequest(BaseModel):
    identifier: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ActivateAccountRequest(BaseModel):
    email: str
    invite_token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, field: str) -> str:
        return validate_password(field)