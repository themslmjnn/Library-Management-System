from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.models.loan_book_model import LoanBook
from src.models.book_inventory_model import BookInventory


class LoanBookRepository:
    @staticmethod
    def loan_book(db: Session, loan_request):
        db.add(loan_request)

        return loan_request
    

    @staticmethod
    def get_loaned_books(db: Session):
        query = select(LoanBook)

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_loaned_book_by_id(db: Session, loaned_book_id):
        query = (
            select(LoanBook)
            .filter(LoanBook.id == loaned_book_id)
        )

        result = db.execute(query)

        return result.scalars().first()

    
    @staticmethod
    def search_loaned_books(db: Session, search_loaned_book_request):
        query = select(LoanBook)

        if search_loaned_book_request.book_id is not None:
            query = query.filter(LoanBook.book_id == search_loaned_book_request.book_id)

        if search_loaned_book_request.user_id is not None:
            query = query.filter(LoanBook.user_id == search_loaned_book_request.user_id)

        if search_loaned_book_request.created_by is not None:
            query = query.filter(LoanBook.created_by == search_loaned_book_request.created_by)

        if search_loaned_book_request.loaned_at is not None:
            query = query.filter(LoanBook.loaned_at == search_loaned_book_request.loaned_at)

        if search_loaned_book_request.due_at is not None:
            query = query.filter(LoanBook.due_at == search_loaned_book_request.due_at)

        result = db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    def get_not_returned_loans(db: Session, book_id: int):
        query = (
            select(func.count())
            .select_from(LoanBook)
            .filter(and_(
                LoanBook.book_id == book_id,
                LoanBook.returned_at.is_(None)
            ))
        )

        result = db.execute(query)

        return result.scalar()
    
    @staticmethod
    def get_loan_by_user_and_book_id(db: Session, book_id: int, user_id: int):
        query = (
            select(LoanBook)
            .filter(and_(
                LoanBook.book_id == book_id,
                LoanBook.user_id == user_id
            ))
        )

        result = db.execute(query)

        return result.scalars().first()

    
    
