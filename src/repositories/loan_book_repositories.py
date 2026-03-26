from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.models.loaned_book_model import LoanedBook


class LoanedBookRepository:
    @staticmethod
    def loan_book(db: Session, loan_request):
        db.add(loan_request)
    
    
    @staticmethod
    def get_all_loans(db: Session):
        query = select(LoanedBook)

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_loan_by_id_admin(db: Session, loan_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.id == loan_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    

    @staticmethod
    def get_loan_by_id_public(db: Session, loan_id, user_id):
        query = (
            select(LoanedBook)
            .filter(and_(
                LoanedBook.id == loan_id,
                LoanedBook.user_id == user_id)
            )
        )

        result = db.execute(query)

        return result.scalars().first()
    
    
    @staticmethod
    def get_loans_by_user_id(db: Session, user_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.user_id == user_id)
        )

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_loans_by_book_id(db: Session, book_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.book_id == book_id)
        )

        result = db.execute(query)

        return result.scalars().all()

    
    @staticmethod
    def search_loans_admin(db: Session, search_request):
        query = select(LoanedBook)

        if search_request.book_id is not None:
            query = query.filter(LoanedBook.book_id == search_request.book_id)

        if search_request.user_id is not None:
            query = query.filter(LoanedBook.user_id == search_request.user_id)

        if search_request.created_by is not None:
            query = query.filter(LoanedBook.created_by == search_request.created_by)

        if search_request.returned_at is not None:
            query = query.filter(LoanedBook.returned_at == search_request.returned_at)

        if search_request.due_at is not None:
            query = query.filter(LoanedBook.due_at == search_request.due_at)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def search_loans_public(db: Session, search_request, user_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.user_id == user_id)
        )

        if search_request.book_id is not None:
            query = query.filter(LoanedBook.book_id == search_request.book_id)

        if search_request.user_id is not None:
            query = query.filter(LoanedBook.user_id == search_request.user_id)

        if search_request.created_by is not None:
            query = query.filter(LoanedBook.created_by == search_request.created_by)

        if search_request.returned_at is not None:
            query = query.filter(LoanedBook.returned_at == search_request.returned_at)

        if search_request.due_at is not None:
            query = query.filter(LoanedBook.due_at == search_request.due_at)

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_not_returned_loans_by_book_id(db: Session, book_id: int):
        query = (
            select(func.count())
            .select_from(LoanedBook)
            .filter(and_(
                LoanedBook.book_id == book_id,
                LoanedBook.returned_at.is_(None)
            ))
        )

        result = db.execute(query)

        return result.scalar()
    
    
    @staticmethod
    def get_number_of_loans_by_user_id(db: Session, user_id):
        query = (
            select(func.count())
            .select_from(LoanedBook)
            .filter(and_(
                LoanedBook.user_id == user_id,
                LoanedBook.returned_at.is_(None))
            )
        )

        result = db.execute(query)

        return result.scalar()