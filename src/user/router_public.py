from fastapi import APIRouter, status

from src.core.dependencies import async_db_dependency
from src.user.schemas import CreateUserPublic, UserResponseBase
from src.user.service import UserServicePublic

router = APIRouter(
    prefix="/users",
    tags=["Users - Public"],
)

@router.post("/me", response_model=UserResponseBase, status_code=status.HTTP_201_CREATED)
async def create_account_public(
    db: async_db_dependency,
    user_request: CreateUserPublic,
):
    return await UserServicePublic.create_account_public(db, user_request)