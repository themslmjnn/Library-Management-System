from fastapi import HTTPException

from sqlalchemy.exc import IntegrityError

from src.models.user_model import User
from src.repositories.auth_repositories import UserRepository


MESSAGE_409 = "Duplicate values are not accepted"
MESSAGE_404 = "User not found"


class UserService:
    @staticmethod
    def register_user(db, user_request, bcrypt_context):
        new_user = User(
            username=user_request.username,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            date_of_birth=user_request.date_of_birth,
            email_address=user_request.email_address,
            hash_password=bcrypt_context.hash(user_request.password),
            role=user_request.role,
            is_active=user_request.is_active
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
    def delete_user_by_id(db, user_id):
        user_model = UserRepository.get_user_by_id(db, user_id)

        if user_model is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
        
        UserRepository.delete_user_by_id(db, user_model)
        db.commit()


    @staticmethod
    def get_user_by_id(db, user_id):
        user_model = UserRepository.get_user_by_id(db, user_id)

        if user_model is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
        
        return user_model
    

    @staticmethod
    def get_all_users(db):
        return UserRepository.get_all_users(db)
    

    @staticmethod
    def update_user_by_id(db, user_request, user_id):
        user_model = UserRepository.get_user_by_id(db, user_id)

        if user_model is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404)
        
        try:
            for field, value in user_request.model_dump(exclude_unset=True).items():
                setattr(user_model, field, value)

            db.commit()
        except IntegrityError:
            db.rollback()
            
            raise HTTPException(status_code=409, detail="Duplicate values are not accepted")
        
        return user_model
    
    
    @staticmethod
    def update_user_password(db, user_request, user_id, bcrypt_context):
        user_model = UserRepository.get_user_by_id(db, user_id)

        if user_model is None:
            raise HTTPException(status_code=404, detail=MESSAGE_404)

        if not bcrypt_context.verify(user_request.old_password, user_model.hash_password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        user_model.hash_password = bcrypt_context.hash(user_request.new_password)
        
        db.commit()

        return {"message": "Password was sucessfully changed"}
    