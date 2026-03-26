from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.models.loaned_book_model import LoanedBook


class LoanedBookRepository:
    @staticmethod
    def loan_book(db: Session, loan_request):
        db.add(loan_request)
    
    
    @staticmethod
    def get_loaned_books(db: Session):
        query = select(LoanedBook)

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_loaned_book_by_id(db: Session, loaned_book_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.id == loaned_book_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    
    
    @staticmethod
    def get_loaned_books_by_user_id(db: Session, user_id):
        query = (
            select(LoanedBook)
            .filter(and_(
                LoanedBook.user_id == user_id,
                LoanedBook.returned_at.is_(None))
            )
        )

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_loaned_books_by_book_id(db: Session, book_id):
        query = (
            select(LoanedBook)
            .filter(LoanedBook.book_id == book_id)
        )

        result = db.execute(query)

        return result.scalars().all()

    
    @staticmethod
    def search_loaned_book(db: Session, search_loaned_book_request):
        query = select(LoanedBook)

        if search_loaned_book_request.book_id is not None:
            query = query.filter(LoanedBook.book_id == search_loaned_book_request.book_id)

        if search_loaned_book_request.user_id is not None:
            query = query.filter(LoanedBook.user_id == search_loaned_book_request.user_id)

        if search_loaned_book_request.created_by is not None:
            query = query.filter(LoanedBook.created_by == search_loaned_book_request.created_by)

        if search_loaned_book_request.loaned_at is not None:
            query = query.filter(LoanedBook.loaned_at == search_loaned_book_request.loaned_at)

        if search_loaned_book_request.due_at is not None:
            query = query.filter(LoanedBook.due_at == search_loaned_book_request.due_at)

        result = db.execute(query)

        return result.scalars().all()
    
    
    @staticmethod
    def get_not_returned_loans(db: Session, book_id: int):
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
    def get_number_of_loaned_books_by_user_id(db: Session, user_id):
        query = (
            select(func.count())
            .filter(and_(
                LoanedBook.user_id == user_id,
                LoanedBook.returned_at.is_(None))
            )
        )

        result = db.execute(query)

        return result.scalar()