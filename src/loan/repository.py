from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.loan.models import Loan
from src.loan.schemas import CreateLoanPublic, LoanBase, SearchLoan, SearchLoanPublic
from src.user.models import User

ALLOWED_SORT_FIELDS_LOAN = {"created_at", "book_id", "user_id", "created_by", "due_at"}


class LoanRepository:
    @staticmethod
    def loan_book(db: AsyncSession, loan_request: CreateLoanPublic | LoanBase) -> None:
        db.add(loan_request)
    
    
    @staticmethod
    async def get_loans(
        db: AsyncSession,
        skip: int,
        limit: int,
        filters: SearchLoan | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Loan], int]:
        
        base_query = select(Loan)

        if filters:
            if filters.book_id is not None:
                base_query = base_query.filter(Loan.book_id == filters.book_id)

            if filters.user_id is not None:
                base_query = base_query.filter(Loan.user_id == filters.user_id)

            if filters.created_by is not None:
                base_query = base_query.filter(Loan.created_by == filters.created_by)

            if filters.returned_at is not None:
                base_query = base_query.filter(Loan.returned_at == filters.returned_at)

            if filters.due_at is not None:
                base_query = base_query.filter(Loan.due_at == filters.due_at)
        
        if sort_by not in ALLOWED_SORT_FIELDS_LOAN:
            sort_by = "created_at"

        sort_column = getattr(Loan, sort_by, Loan.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total
    
    
    @staticmethod
    async def get_loan_by_id(db: AsyncSession, loan_id: int) -> Loan | None:
        query = (
            select(Loan)
            .filter(Loan.id == loan_id)
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()
    
    
    @staticmethod
    async def get_not_returned_loans_by_book_id(db: AsyncSession, book_id: int) -> int:
        query = (
            select(func.count())
            .select_from(Loan)
            .filter(and_(
                Loan.book_id == book_id,
                Loan.returned_at.is_(None)
            ))
        )

        result = await db.execute(query)

        return result.scalar()
    
    
class LoanRepositoryPublic:
    @staticmethod
    async def get_loans_public(
        db: AsyncSession,
        skip: int,
        limit: int,
        current_user: User,
        filters: SearchLoanPublic | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Loan], int]:
        
        base_query = (
            select(Loan)
            .filter(Loan.user_id == current_user.id)
        )

        if filters:
            if filters.book_id is not None:
                base_query = base_query.filter(Loan.book_id == filters.book_id)

            if filters.returned_at is not None:
                base_query = base_query.filter(Loan.returned_at == filters.returned_at)

            if filters.due_at is not None:
                base_query = base_query.filter(Loan.due_at == filters.due_at)
        
        if sort_by not in ALLOWED_SORT_FIELDS_LOAN:
            sort_by = "created_at"

        sort_column = getattr(Loan, sort_by, Loan.created_at)
        if order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        count_result = await db.execute(
            select(func.count())
            .select_from(base_query.subquery())
        )

        total  = count_result.scalar_one()

        result = await db.execute(
            base_query.offset(skip).limit(limit)
        )

        return result.scalars().all(), total
    
    @staticmethod
    async def get_loan_by_id_public(db: AsyncSession, current_user: User, loan_id: int) -> Loan | None:
        query = (
            select(Loan)
            .filter(
                and_(
                    Loan.id == loan_id,
                    Loan.user_id == current_user.id,
                )
            )
        )

        result = await db.execute(query)

        return result.scalar_one_or_none()