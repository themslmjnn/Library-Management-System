from fastapi import APIRouter, status, Depends
from src.core.dependencies import async_db_dependency
from src.user.schemas import CreateUserStaff, UserResponseStaff
from src.user.service import UserServiceStaff
from src.core.dependencies import require_roles
from typing import Annotated
from src.user.models import User, UserRole

router = APIRouter(
    prefix="/users",
    tags=["Users - Staff"],
)

@router.post("/staff", response_model=UserResponseStaff, status_code=status.HTTP_201_CREATED)
async def create_account_public(
    db: async_db_dependency,
    user_request: CreateUserStaff,
    current_user: Annotated[User, Depends(require_roles((UserRole.library_admin, UserRole.receptionist)))],
):
    return await UserServiceStaff.create_account_staff(db, user_request, current_user)