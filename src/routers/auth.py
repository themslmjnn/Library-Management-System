from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from starlette import status
from typing import Annotated
from passlib.context import CryptContext

from db.database import get_db
from schemas.auth_schemas import UserCreatePublic, UserResponse, UserUpdate, UserUpdatePassword
from services.auth_services import UserService


router = APIRouter(
    tags=["Auth"]
)

db_dependency = Annotated[Session, Depends(get_db)]

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MESSAGE_404 = "User not found"


@router.post("/auth", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(db: db_dependency, user_request: UserCreatePublic):
    return UserService.register_user(db, user_request, bcrypt_context)


@router.delete("/auth/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_id(db: db_dependency, user_id: Annotated[int, Path(ge=1)]):
    UserService.delete_user_by_id(db, user_id)


@router.get("/auth", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
def get_all_users(db: db_dependency):
    return UserService.get_all_users(db)


@router.get("/auth/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user_by_id(db: db_dependency, user_id: Annotated[int, Path(ge=1)]):
    return UserService.get_user_by_id(db, user_id)


@router.put("/auth/personal_info/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_users_by_id(db: db_dependency, user_request: UserUpdate, user_id: Annotated[int, Path(ge=1)]):
    return UserService.update_user_by_id(db, user_request, user_id)


@router.put("/auth/password/{user_id}", status_code=status.HTTP_200_OK)
def update_user_password(db: db_dependency, user_request: UserUpdatePassword, user_id: Annotated[int, Path(ge=1)]):
    return UserService.update_user_password(db, user_request, user_id, bcrypt_context)