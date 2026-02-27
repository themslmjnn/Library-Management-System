from sqlalchemy import select
from sqlalchemy.orm import Session

from models.loaned_books_model import LoanedBook


class LoaningBookRepository:
    @staticmethod
    def loan_book(db: Session, loan_request):
        db.add(loan_request)

        return loan_request
    

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
    def delete_loaned_book_by_id(db: Session, loaned_book):
        db.delete(loaned_book)