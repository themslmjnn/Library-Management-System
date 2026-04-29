from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    pagination_dependency,
    require_roles,
)
from src.loan.schemas import LoanBase, LoanResponse, SearchLoan
from src.loan.service import LoanService
from src.pagination import PaginatedResponse
from src.user.models import User, UserRole
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/loans",
    tags=["Loans"]
)


@router.get("", response_model=PaginatedResponse[LoanResponse], status_code=status.HTTP_200_OK)
async def get_loans(
    db: async_db_dependency,
    pagination: pagination_dependency,
    _: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist))],
    filters: Annotated[SearchLoan, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await LoanService.get_loans(
        db,
        pagination.skip,
        pagination.limit,
        filters,
        sort_by,
        order
    )


@router.get("/{loan_id}", response_model=LoanResponse, status_code=status.HTTP_200_OK)
async def get_loan_by_id(
    db: async_db_dependency, 
    _: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist))],
    loan_id: path_param_int_ge1,
):
    return await LoanService.get_loan_by_id(db, loan_id)


@router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def loan_book(
    db: async_db_dependency, 
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist))],
    loan_request: LoanBase
):
    return await LoanService.loan_book(db, current_user.id, loan_request)


@router.put("/{loan_id}/return", response_model=LoanResponse, status_code=status.HTTP_200_OK)
async def return_loan(
    db: async_db_dependency, 
    current_user: Annotated[User, Depends(require_roles(UserRole.system_admin, UserRole.library_admin, UserRole.receptionist))],
    loan_id: path_param_int_ge1,
):    
    return await LoanService.return_loan(db, current_user.id, loan_id)