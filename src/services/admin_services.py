from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from src.models import user_model, book_model, book_inventory_model
from src.repositories.auth_repositories import UserRepository
from src.repositories.book_repositories import BookRepository
from src.repositories.book_inventory_repositories import BookInventoryRepository
from src.repositories.loan_book_repositories import LoanBookRepository


MESSAGE_403 = "Accessing denied"
MESSAGE_404_1 = "User not found"
MESSAGE_404_2 = "Book not found"
MESSAGE_404_3 = "Book inventory not found"
MESSAGE_404_4 = "Loaned book not found"
MESSAGE_409 = "Duplicate values are not accepted"


class AdminAuthService:
    @staticmethod
    def register_user(db, user, user_request, bcrypt_context):
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail=MESSAGE_403)

        new_user = user_model.User(\
            username=user_request.username,
            first_name=user_request.first_name.title(),
            last_name=user_request.last_name.title(),
            date_of_birth=user_request.date_of_birth,
            email_address=user_request.email_address,
            hash_password=bcrypt_context.hash(user_request.password),
            role=user_request.role,
            created_by=user["id"]
        )

        try:
            UserRepository.register_user(db, new_user)

            db.commit()
            db.refresh(new_user)
            
            return new_user
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
    

    @staticmethod 
    def get_all_users(db, user):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return UserRepository.get_all_users(db)

    
    @staticmethod
    def search_users(db, user, search_user_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return UserRepository.search_users(db, search_user_request)
        

class AdminBookService:
    @staticmethod
    def add_book(db, user, book_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        new_book = book_model.Book(\
            title=book_request.title.title(),
            author=book_request.author.title(),
            category=book_request.category,
            description=book_request.description.title(),
            rating=book_request.rating,
            publishing_date=book_request.publishing_date,
            created_by=user["id"]
        )

        try:
            BookRepository.add_book(db, new_book)

            db.commit()
            db.refresh(new_book)

            return new_book
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)
    
    
    @staticmethod 
    def get_all_books(db, user):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)

        return BookRepository.get_all_books(db)
    
    
    @staticmethod
    def get_book_by_id(db, user, book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        book = BookRepository.get_book_by_id(db, book_id)

        if book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_2)
        
        return book
    
    
    @staticmethod
    def search_books(db, user, search_book_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return BookRepository.search_books(db, search_book_request)
    
    
    @staticmethod
    def update_book_info_by_book_id(db, user, book_request, book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        book = BookRepository.get_book_by_id(db, book_id)

        if book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_2)
        
        try:
            for field, value in book_request.model_dump(exclude_unset=True).items():
                if field in ("title", "author"):
                    setattr(book, field, value.title())
                else:
                    setattr(book, field, value)

            db.commit()

            return book

        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)


class AdminBookInventoryService:
    @staticmethod
    def add_book_inventory(db, user, book_inventory_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)

        new_book_inventory = book_inventory_model.BookInventory(\
            book_id=book_inventory_request.book_id,
            added_by=user["id"],
            quantity_added=book_inventory_request.quantity_added
        )

        try:
            BookInventoryRepository.add_book_inventory(db, new_book_inventory)

            db.commit()
            db.refresh(new_book_inventory)

            return new_book_inventory
        
        except IntegrityError:
            db.rollback()

            raise HTTPException(status_code=409, detail=MESSAGE_409)

    
    @staticmethod
    def get_all_books_inventory(db, user):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return BookInventoryRepository.get_all_book_inventory(db)
    

    @staticmethod
    def get_book_inventory_by_id(db, user, book_inventory_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)

        book_inventory = BookInventoryRepository.get_book_inventory_by_id(db, book_inventory_id)

        if book_inventory is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_3)
        
        return book_inventory
    

    @staticmethod
    def search_books_inventory(db, user, search_book_inventory_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return BookInventoryRepository.search_book_inventory(db, search_book_inventory_request)
    
    
    @staticmethod
    def update_book_inventory_quantity_by_id(db, user, quantity, book_inventory_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)

        book_inventory = BookInventoryRepository.get_book_inventory_by_id(db, book_inventory_id)

        if book_inventory is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_3)
        
        book_inventory.quantity_added = quantity

        db.commit()

        return book_inventory
    

class AdminLoanBookService:
    @staticmethod
    def get_loaned_books(db, user):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return LoanBookRepository.get_loaned_books(db)
    
    
    @staticmethod
    def get_loaned_book_by_id(db, user, loaned_book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        loaned_book = LoanBookRepository.get_loaned_book_by_id(db, loaned_book_id)

        if loaned_book is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404_4)
        
        return loaned_book
    
    
    @staticmethod
    def search_loaned_books(db, user, search_loaned_book_request):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        return LoanBookRepository.search_loaned_books(db, search_loaned_book_request)


    @staticmethod
    def get_loaned_books_by_book_id(db, user, book_id):
        if user["role"] not in ("admin", "member"):
            raise HTTPException(status_code=403, detail=MESSAGE_403)
        
        loaned_books = LoanBookRepository.get_loaned_books_by_book_id(db, book_id)

        return loaned_books