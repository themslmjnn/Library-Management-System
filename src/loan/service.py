from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.book.repository import BookRepository
from src.core.cache import get_cache, set_cache
from src.core.logging import get_logger
from src.inventory.repository import InventoryRepository
from src.loan.models import Loan
from src.loan.repository import LoanRepository, LoanRepositoryPublic
from src.loan.schemas import (
    CreateLoanPublic,
    LoanBase,
    LoanResponse,
    SearchLoan,
    SearchLoanPublic,
)
from src.pagination import PaginatedResponse
from src.user.models import User
from src.user.repository import UserRepositoryBase
from src.utils.cache_keys import loan_detail_key
from src.utils.exception_constants import HTTP404, HTTP409
from src.utils.exceptions import (
    BookNotAvailableError,
    BookNotFoundError,
    LoanAlreadyReturnedError,
    LoanNotFoundError,
    UserNotFoundError,
)
from src.utils.helpers import ensure_exists

logger = get_logger(__name__)

    
class LoanService:
    @staticmethod
    async def loan_book(db: AsyncSession, current_user_id: int, loan_request: LoanBase) -> Loan:
     
        user = await UserRepositoryBase.get_user_by_id(db, loan_request.user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))
            
        book = await BookRepository.get_book_by_id(db, loan_request.book_id)
        ensure_exists(book, BookNotFoundError(HTTP404.BOOK))
            
        book_available = await InventoryRepository.get_available_inventories(db, loan_request.book_id)
        
        if not isinstance(book_available, list) or len(book_available) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=HTTP404.BOOK_NOT_AVAILABLE,
            )
        
        new_loan = Loan(
            **loan_request.model_dump(),
            inventory_id=book_available[0].id,
            created_by=current_user_id,
        )

        try:
            LoanRepository.loan_book(db, new_loan)

            inventory = await InventoryRepository.get_inventory_by_id(db, new_loan.inventory_id)
            inventory.quantity -= 1

            await db.commit()
            await db.refresh(new_loan)

            logger.info(
                "loan_created",
                loan_id=new_loan.id,
                user_id=new_loan.user_id,
                created_by=current_user_id,
            )

            return new_loan
        except IntegrityError as e:
            await db.rollback()

            logger.error(
                "create_loan_failed",
                user_id=new_loan.user_id,
                requested_by=current_user_id,
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
    async def get_loan_by_id(db: AsyncSession, loan_id: int) -> LoanResponse:
        key = loan_detail_key(loan_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached
        
        loan = await LoanRepository.get_loan_by_id(db, loan_id)
        ensure_exists(loan, LoanNotFoundError(HTTP404.LOAN))

        serialized = LoanResponse.model_validate(loan).model_dump(mode="json")
        await set_cache(key, serialized, 600)
        
        return serialized
    

    @staticmethod
    async def return_loan(db: AsyncSession, current_user: User, loan_id: int) -> Loan:         
        loan = await LoanRepository.get_loan_by_id(db, loan_id)
        ensure_exists(loan, LoanNotFoundError(HTTP404.LOAN))
            
        if loan.returned_at is not None:
            logger.warning(
                "return_loan_failed",
                loan_id=loan_id,
                requested_by=current_user.id,
                reason="loan_is_already_returned"
            )

            raise LoanAlreadyReturnedError("Loan is already returned")
            
        loan.returned_at = datetime.now(timezone.utc)

        inventory = await InventoryRepository.get_inventory_by_id(db, loan.inventory_id)
        inventory.quantity += 1

        await db.commit()

        return loan


class LoanServicePublic:
    @staticmethod
    async def loan_book_me(db: AsyncSession, loan_request: CreateLoanPublic, user_id: int) -> Loan:
        user = await UserRepositoryBase.get_user_by_id(db, user_id)
        ensure_exists(user, UserNotFoundError(HTTP404.USER))
            
        book = await BookRepository.get_book_by_id(db, loan_request.book_id)
        ensure_exists(book, BookNotFoundError(HTTP404.BOOK))
        
        book_available = await InventoryRepository.get_available_inventories(db, loan_request.book_id)
        
        if not isinstance(book_available, list) or len(book_available) == 0:
            raise BookNotAvailableError(HTTP404.BOOK_NOT_AVAILABLE)
        
        new_loan = Loan(
            **loan_request.model_dump(),
            user_id=user_id,
            inventory_id=book_available[0].id,
            created_by=user_id,
        )
        
        try:
            LoanRepository.loan_book(db, new_loan)

            inventory = await InventoryRepository.get_inventory_by_id(db, new_loan.inventory_id)
            inventory.quantity -= 1

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
            await db.rollback()

            logger.error(
                "create_loan_failed",
                user_id=new_loan.user_id,
                method="self-loaned",
                error=str(e.orig),
            )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=HTTP409.LOAN,
            )
        

    @staticmethod
    async def get_loans_me(
        db: AsyncSession,
        skip: int,
        limit: int,
        user_id: int,
        filters: SearchLoanPublic,
        sort_by: str,
        order: str,
    ) -> PaginatedResponse:
        
        loans, total = await LoanRepositoryPublic.get_loans_me(db, user_id, skip, limit, filters, sort_by, order)

        return PaginatedResponse(
            items=loans,
            total=total,
            skip=skip,
            limit=limit,
            has_more=skip + limit < total,
        )
    

    @staticmethod
    async def get_loan_by_id_me(db: AsyncSession, user_id: int, loan_id: int) -> LoanResponse:
        key = loan_detail_key(loan_id)
        cached = await get_cache(key)
        if cached is not None:
            return cached
                
        loan = await LoanRepositoryPublic.get_loan_by_id_me(db, user_id, loan_id)
        ensure_exists(loan, LoanNotFoundError(HTTP404.LOAN))

        serialized = LoanResponse.model_validate(loan).model_dump(mode="json")
        await set_cache(key, serialized, 600)
        
        return serialized