from fastapi import HTTPException, status

from src.models.user_model import UserRole
from src.utils.constants import MESSAGE_403_FORBIDDEN


def require_admin(user) -> None:
    if user["role"] != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403_FORBIDDEN)


def require_user(user, owner_id) -> None:
    if user["id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403_FORBIDDEN)


def require_admin_or_owner(user, owner_id) -> None:
    if user["role"] != UserRole.admin and user["id"] != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403_FORBIDDEN)
    

def require_admin_or_member(user) -> None:
    if user["role"] not in (UserRole.admin, UserRole.member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403_FORBIDDEN)


def is_both_admin(current_user, user_to_be_deleted) -> None:
    if current_user["role"] == UserRole.admin and user_to_be_deleted.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MESSAGE_403_FORBIDDEN)
    

def ensure_exists(object, message) -> None:
    if object is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
     

def update_object(instance, request) -> None:
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(instance, field, value)