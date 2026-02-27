from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from models.loaning_books_model import LoanedBook
from repositories.loaning_books_repositories import LoaningBookRepository


MESSAGE_409 = "Duplicate values are not accepted"
MESSAGE_404 = "Book not found"


class LoaningBookService:
    @staticmethod
    def loan_book(db, loan_request):
        new_request = LoanedBook(**loan_request.model_dump())

        try:
            LoaningBookRepository.loan_book(db, new_request)

            db.commit()
            db.refresh(new_request)

            return new_request
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
        

    @staticmethod
    def get_loaned_books(db):
        return LoaningBookRepository.get_loaned_books(db)
    

    @staticmethod
    def get_loaned_book_by_id(db, loaned_book_id):
        loaned_book_model = LoaningBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        if not loaned_book_model:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
        
        return loaned_book_model
    
    
    @staticmethod
    def delete_loaned_book_id(db, loaned_book_id):
        loaned_book_model = LoaningBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        if not loaned_book_model:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
        
        LoaningBookRepository.delete_loaned_book_by_id(loaned_book_model)

        db.commit()


