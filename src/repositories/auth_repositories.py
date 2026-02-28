from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user_model import User


class UserRepository:
    @staticmethod
    def register_user(db: Session, new_user):
        db.add(new_user)

        return new_user
    

    @staticmethod
    def delete_user_by_id(db: Session, user):
        db.delete(user)


    @staticmethod
    def get_user_by_id(db: Session, user_id):
        query = (
            select(User)
            .filter(User.id == user_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    
    
    @staticmethod
    def get_all_users(db: Session):
        query = select(User)

        result = db.execute(query)

        return result.scalars().all()
    
    @staticmethod
    def search_users(db: Session, search_user_request):
        query = select(User)

        if search_user_request.username:
            query = query.filter(User.username.ilike(search_user_request.username))

        if search_user_request.first_name:
            query = query.filter(User.first_name.ilike(search_user_request.first_name))

        if search_user_request.last_name:
            query = query.filter(User.last_name.ilike(search_user_request.last_name))

        if search_user_request.date_of_birth:
            query = query.filter(User.date_of_birth == search_user_request.date_of_birth)

        if search_user_request.email_address:
            query = query.filter(User.email_address.ilike(search_user_request.email_address))

        if search_user_request.role:
            query = query.filter(User.role.ilike(search_user_request.role))

        if search_user_request.is_active is not None:
            query = query.filter(User.is_active == search_user_request.is_active)

        result = db.execute(query)

        return result.scalars().all()