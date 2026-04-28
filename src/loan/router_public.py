from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.dependencies import (
    async_db_dependency,
    current_user_dependency,
    pagination_dependency,
)
from src.loan.schemas import CreateLoanPublic, LoanResponse, SearchLoanPublic
from src.loan.service import LoanServicePublic
from src.pagination import PaginatedResponse
from src.utils.exception_constants import path_param_int_ge1

router = APIRouter(
    prefix="/loans",
    tags=["Loans - Public"],
)


@router.post("/me", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def loan_book_me(
    db: async_db_dependency,
    loan_request: CreateLoanPublic,
    current_user: current_user_dependency,
):
    return await LoanServicePublic.loan_book_me(db, loan_request, current_user.id)


@router.get("/me", response_model=PaginatedResponse[LoanResponse], status_code=status.HTTP_200_OK)
async def get_loans_me(
    db: async_db_dependency,
    pagination: pagination_dependency,
    current_user: current_user_dependency,
    filters: Annotated[SearchLoanPublic, Depends()],
    sort_by: str = "created_at",
    order: str = "desc",
):
    return await LoanServicePublic.get_loans_me(
        db,
        pagination.skip,
        pagination.limit,
        current_user.id,
        filters,
        sort_by,
        order
    )


@router.get("/{loan_id}/me", response_model=LoanResponse, status_code=status.HTTP_200_OK)
async def get_loan_by_id_me(
    db: async_db_dependency, 
    current_user: current_user_dependency,
    loan_id: path_param_int_ge1,
):
    return await LoanServicePublic.get_loan_by_id_me(db, current_user.id, loan_id)