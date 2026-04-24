from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from book.repository import BookRepository
from src.core.logging import get_logger
from src.inventory.repository import InventoryRepository
from src.loan.models import Loan
from src.loan.repository import LoanRepository, LoanRepositoryPublic
from src.loan.schemas import CreateLoanPublic, LoanBase, SearchLoan, SearchLoanPublic
from src.pagination import PaginatedResponse
from src.utils.exception_constants import HTTP404, HTTP409
from src.utils.helpers import ensure_exists
from user.models import User
from user.repository import UserRepositoryBase

logger = get_logger(__name__)

    
class LoanService:
    @staticmethod
    async def loan_book(
        db: AsyncSession,
        loan_request: LoanBase,
        current_user: User,
    ):
        new_loan = Loan(
            book_id=loan_request.book_id,
            user_id=current_user.id,
            due_at=loan_request.due_at,
            created_by=current_user.id,
        )

        user = await UserRepositoryBase.get_user_by_id(db, loan_request.user_id)

        ensure_exists(user, HTTP404.USER)
            
        book = await BookRepository.get_book_by_id(db, new_loan.book_id)

        ensure_exists(book, HTTP404.BOOK)
            
        quantity = await InventoryRepository.get_quantity_added(db, new_loan.book_id) or 0
            
        book_available = quantity - await LoanRepository.get_not_returned_loans(db, new_loan.book_id)

        if book_available <= 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=HTTP404.BOOK_NOT_AVAILABLE,
            )
        

        try:
            LoanRepository.loan_book(db, new_loan)

            await db.commit()
            await db.refresh(new_loan)

            logger.info(
                "loan_created",
                loan_id=new_loan.id,
                user_id=new_loan.user_id,
                created_by=current_user.id,
            )

            return new_loan
        
        except IntegrityError as e:
            logger.error(
                "loan_creation_failed",
                user_id=new_loan.user_id,
                requested_by=current_user.id,
                error=str(e.orig),
            )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=HTTP409.LOAN,
            )

    @staticmethod
    async def get_loans(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchLoan,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        loans, total = await LoanRepository.get_loans(db, skip, limit, filters, sort_by, order)

        return PaginatedResponse(
            items=loans,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    
    @staticmethod
    async def get_loan_by_id(db: AsyncSession, loan_id: int) -> Loan:
        loan = await LoanRepository.get_loan_by_id(db, loan_id)

        ensure_exists(loan, HTTP404.LOAN)
        
        return loan
    
    @staticmethod
    async def return_loan(db: AsyncSession, current_user: User, loan_id: int) -> None:         
        loan = await LoanRepository.get_loan_by_id(db, loan_id)

        ensure_exists(loan, HTTP404.LOAN)
            
        if loan.returned_at is not None:
            logger.warning(
                "loan_returning_failed",
                loan_id=loan_id,
                requested_by=current_user.id,
                reason="Loan is already returned"
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Loan is already returned",
            )
            
        loan.returned_at = datetime.now()

        await db.commit()

class LoanServicePublic:
    @staticmethod
    async def loan_book_public(
        db: AsyncSession,
        loan_request: CreateLoanPublic,
        current_user: User,
    ):
        new_loan = Loan(
            book_id=loan_request.book_id,
            user_id=current_user.id,
            due_at=loan_request.due_at
        )

        user = await UserRepositoryBase.get_user_by_id(db, loan_request.user_id)

        ensure_exists(user, HTTP404.USER)
            
        book = await BookRepository.get_book_by_id(db, new_loan.book_id)

        ensure_exists(book, HTTP404.BOOK)
            
        quantity = await InventoryRepository.get_quantity_added(db, new_loan.book_id) or 0
            
        book_available = quantity - await LoanRepository.get_not_returned_loans(db, new_loan.book_id)

        if book_available <= 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=HTTP404.BOOK_NOT_AVAILABLE,
            )
        
        try:
            LoanRepository.loan_book(db, new_loan)

            await db.commit()
            await db.refresh(new_loan)

            logger.info(
                "loan_created",
                loan_id=new_loan.id,
                user_id=new_loan.user_id,
                method="self-loaned",
            )

            return new_loan
        
        except IntegrityError as e:
            logger.error(
                "loan_creation_failed",
                user_id=new_loan.user_id,
                method="self-loaned",
                error=str(e.orig),
            )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=HTTP409.LOAN,
            )
        
    @staticmethod
    async def get_loans_public(
        db: AsyncSession,
        skip: int,
        limit: int,
        current_user: User,
        filters: SearchLoanPublic,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        loans, total = await LoanRepositoryPublic.get_loans_public(db, current_user, skip, limit, filters, sort_by, order)

        return PaginatedResponse(
            items=loans,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    
    @staticmethod
    async def get_loan_by_id_public(db: AsyncSession, current_user: User, loan_id: int) -> Loan:        
        loan = await LoanRepositoryPublic.get_loan_by_id_public(db, loan_id, current_user.id)

        ensure_exists(loan, HTTP404.LOAN)
        
        return loan
    
    @staticmethod
    async def return_loan_public(db: AsyncSession, current_user: User, loan_id: int) -> None:         
        loan = await LoanRepositoryPublic.get_loan_by_id_public(db, current_user, loan_id)

        ensure_exists(loan, HTTP404.LOAN)
            
        if loan.returned_at is not None:
            logger.warning(
                "loan_returning_failed",
                loan_id=loan_id,
                reason="Loan is already returned"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Loan is already returned",
            )
            
        loan.returned_at = datetime.now()
        
        await db.commit()