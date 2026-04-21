from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    require_roles,
)
from src.user.models import User, UserRole
from src.user.schemas import CreateUserAdmin, UserResponseAdmin
from src.user.service import UserServiceAdmin

router = APIRouter(
    prefix="/users",
    tags=["Users - Admin"],
)


@router.post("", response_model=UserResponseAdmin, status_code=status.HTTP_201_CREATED)
async def create_account_admin(
    db: async_db_dependency,
    user_request: CreateUserAdmin,
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin))],
):
    return await UserServiceAdmin.create_account_admin(db, user_request, current_user)