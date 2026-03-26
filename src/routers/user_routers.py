from fastapi import APIRouter, Depends, Path, status

from typing import Annotated

from db.database import db_dependency
from src.core.security import user_dependency
from src.services.user_services import UserService
from src.schemas.user_schemas import UserActivateAccountPublic, UserCreatePublic, UserResponsePublic1, UserResponsePublic2
from src.schemas.user_schemas import UserUpdatePasswordPublic, UserUpdatePublic, UserUpdateResponsePublic
from src.schemas.user_schemas import UserCreateAdmin, UserResponseAdmin1, UserUpdateAdmin, UserUpdatePasswordAdmin, UserResponseAdmin2, UserUpdateResponseAdmin
from src.schemas.user_schemas import UserSearch


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post("/register/public", response_model=UserResponsePublic1, status_code=status.HTTP_200_OK)
def register_user_public(
        db: db_dependency,
        user_request: UserCreatePublic):
    
    return UserService.register_user_public(db, user_request)


@router.post("/register", response_model=UserResponseAdmin1, status_code=status.HTTP_200_OK)
def register_user(
        db: db_dependency,
        user_request: UserCreateAdmin,
        current_user: user_dependency):
    
    return UserService.register_user_admin(db, current_user, user_request)


@router.get("", response_model=list[UserResponseAdmin2], status_code=status.HTTP_200_OK)
def get_all_users(
        db: db_dependency, 
        current_user: user_dependency):
       
    return UserService.get_all_users(db, current_user)


@router.get("/search", response_model=list[UserResponseAdmin2], status_code=status.HTTP_200_OK)
def search_users(
        db: db_dependency,
        current_user: user_dependency,
        users_request: Annotated[UserSearch, Depends()]):
    
    return UserService.search_users(db, current_user, users_request)


@router.get("/{user_id}", response_model=UserResponseAdmin2, status_code=status.HTTP_200_OK)
def get_user_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):
    
    return UserService.get_user_by_id_admin(db, current_user, user_id)


@router.get("/by_id/public", response_model=UserResponsePublic2, status_code=status.HTTP_200_OK)
def get_user_by_id_public(
        db: db_dependency, 
        current_user: user_dependency):
    
    return UserService.get_user_by_id_public(db, current_user)


@router.delete("/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):

    UserService.delete_user_by_id(db, current_user, user_id)


@router.patch("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
def activate_account(
        db: db_dependency, 
        current_user: user_dependency,
        user_id: Annotated[int, Path(ge=1)]):
    
    return UserService.activate_account_admin(db, current_user, user_id)


@router.patch("/activate/public", status_code=status.HTTP_204_NO_CONTENT)
def activate_account_public(
        db: db_dependency, 
        current_user: user_dependency,
        activate_account_request: UserActivateAccountPublic):
    
    return UserService.activate_account_public(db, current_user, activate_account_request)


@router.patch("/{user_id}/update", response_model=UserUpdateResponseAdmin, status_code=status.HTTP_200_OK)
def update_user(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        update_request: UserUpdateAdmin):
    
    return UserService.update_user_admin(db, current_user, user_id, update_request)


@router.patch("/{user_id}/update/public", response_model=UserUpdateResponsePublic, status_code=status.HTTP_200_OK)
def update_user_public(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        update_request: UserUpdatePublic):
    
    return UserService.update_user_public(db, current_user, user_id, update_request)


@router.put("/update_password/public", status_code=status.HTTP_204_NO_CONTENT)
def update_password_public(
        db: db_dependency,
        current_user: user_dependency,
        update_request: UserUpdatePasswordPublic):
    
    UserService.update_password_public(db, current_user, update_request)


@router.put("/{user_id}/update_password", status_code=status.HTTP_204_NO_CONTENT)
def update_password_admin(
        db: db_dependency,
        current_user: user_dependency,
        user_id: int,
        update_request: UserUpdatePasswordAdmin):
    
    UserService.update_password_admin(db, current_user, user_id, update_request)