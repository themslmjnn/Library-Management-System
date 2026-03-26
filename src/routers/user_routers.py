from fastapi import APIRouter, Depends, Path, status

from typing import Annotated

from db.database import db_dependency
from core.security import user_dependency
from src.services.user_services import UserService
from src.schemas.user_schemas import UserCreatePublic, UserResponsePublic, UserUpdatePasswordPublic, UserUpdatePublic, UserUpdateResponsePublic
from src.schemas.user_schemas import UserCreateAdmin, UserResponseAdmin, UserUpdateAdmin, UserUpdatePasswordAdmin
from src.schemas.user_schemas import UserSearch


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/register/public", response_model=UserResponsePublic, status_code=status.HTTP_200_OK)
def register_user_public(
        db: db_dependency,
        user_request: UserCreatePublic):
    
    return UserService.register_user_public(db, user_request)


@router.post("/register/admin", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK)
def register_user_admin(
        db: db_dependency,
        user_request: UserCreateAdmin,
        current_user: user_dependency):
    
    return UserService.register_user_admin(db, current_user, user_request)


@router.get("", response_model=list[UserResponseAdmin], status_code=status.HTTP_200_OK)
def get_all_users(
        db: db_dependency, 
        current_user: user_dependency):
       
    return UserService.get_all_users(db, current_user)


@router.get("/search", response_model=list[UserResponseAdmin], status_code=status.HTTP_200_OK)
def search_users(
        db: db_dependency,
        current_user: user_dependency,
        users_request: Annotated[UserSearch, Depends()]):
    
    return UserService.search_users(db, current_user, users_request)


@router.get("/{user_id}/admin", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK)
def get_user_by_id_admin(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):
    
    return UserService.get_user_by_id_admin(db, current_user, user_id)


@router.get("/{user_id}/public", response_model=UserResponsePublic, status_code=status.HTTP_200_OK)
def get_user_by_id_public(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):
    
    return UserService.get_user_by_id_public(db, current_user, user_id)


@router.delete("/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):

    UserService.delete_user_by_id(db, current_user, user_id)


@router.patch("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
def activate_user_account(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):
    
    return UserService.activate_user_account(db, current_user, user_id)


@router.patch("/{user_id}/update_info/admin", response_model=UserResponseAdmin, status_code=status.HTTP_200_OK)
def update_user_info_admin(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        user_request: UserUpdateAdmin):
    
    return UserService.update_user_info_admin(db, current_user, user_id, user_request)


@router.patch("/{user_id}/update_info/public", response_model=UserUpdateResponsePublic, status_code=status.HTTP_200_OK)
def update_user_info_public(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        user_request: UserUpdatePublic):
    
    return UserService.update_user_info_public(db, current_user, user_id, user_request)


@router.put("/{user_id}/update_password/public", status_code=status.HTTP_204_NO_CONTENT)
def update_user_password_public(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        user_password_request: UserUpdatePasswordPublic):
    
    UserService.update_user_password_public(db, current_user, user_id, user_password_request)


@router.put("/{user_id}/update_password/admin", status_code=status.HTTP_204_NO_CONTENT)
def update_user_password_admin(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        user_password_request: UserUpdatePasswordAdmin):
    
    UserService.update_user_password_admin(db, current_user, user_id, user_password_request)