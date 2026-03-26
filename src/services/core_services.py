from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from core.core_methods import LoanBookLogic, ReturnLoanLogic
from src.models.user_model import User
from repositories.user_repositories import UserRepository
from src.repositories.loan_book_repositories import LoanBookRepository


MESSAGE_403 = "Accessing denied"
MESSAGE_404_1 = "User not found"
MESSAGE_404_2 = "Book not found"
MESSAGE_404_3 = "Book inventory not found"
MESSAGE_404_4 = "Loaned book not found"
MESSAGE_409 = "Duplicate values are not accepted"


class CoreService:

    @staticmethod
    def get_user_by_id(db, user, user_id):
        if user["role"] not in ("admin", "member") and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        user = UserRepository.get_user_by_id(db, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        return user


    @staticmethod
    def delete_user_by_id(db, user, user_id):
        if user["role"] != "admin" and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        user = UserRepository.get_user_by_id(db, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        loans = LoanBookRepository.get_number_of_loaned_books_by_user_id(db, user_id)

        if loans != 0:
            raise HTTPException(status_code=400, detail="User has loan(s)")
        
        user.is_active = False

        db.commit()


    @staticmethod
    def update_user_info_by_user_id(db, user, user_request, user_id):
        if user["role"] != "admin" and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        user = UserRepository.get_user_by_id(db, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        try:
            for field, value in user_request.model_dump(exclude_unset=True).items():
                if field in ("title", "author"):
                    setattr(user, field, value.title())
                else:
                    setattr(user, field, value)

            db.commit()

            return user
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
        

    @staticmethod
    def update_user_password_by_user_id(db, user, user_password_request, user_id, bcrypt_context):
        if user["role"] != "admin" and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        user = UserRepository.get_user_by_id(db, user_id)

        if user is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_1)
        
        if not bcrypt_context.verify(user_password_request.old_password, user.hash_password):
            raise HTTPException(status_code=400, detail="Incorrect old password")
        
        user.hash_password = bcrypt_context.hash(user_password_request.new_password)

        db.commit()


    @staticmethod
    def loan_book(db, user, loan_book_request):
        if user["role"] not in ("admin", "member") and user["id"] != loan_book_request.user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        new_loan = LoanBookLogic.loan_book(db, loan_book_request, user["id"])

        db.commit()
        db.refresh(new_loan)

        return new_loan
    

    @staticmethod
    def return_loan(db, user, user_id, loan_id):
        if user["role"] not in ("admin", "member") and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
         
        returned_loan = ReturnLoanLogic.return_loan(db, loan_id)

        db.commit()

        return returned_loan


    @staticmethod
    def get_loaned_books_by_user_id(db, user, user_id):
        if user["role"] not in ("admin", "member") and user["id"] != user_id:
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        loaned_books = LoanBookRepository.get_loaned_books_by_user_id(db, user_id)

        return loaned_books

