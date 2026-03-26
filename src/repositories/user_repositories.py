from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user_model import User, UserRole


class UserRepository:
    @staticmethod
    def add_user(db: Session, new_user):
        db.add(new_user)


    @staticmethod
    def get_all_non_admin_users(db: Session):
        query = (
            select(User)
            .filter(User.role != UserRole.admin)
        )

        result = db.execute(query)

        return result.scalars().all()
    

    @staticmethod
    def get_user_by_id(db: Session, user_id):
        query = (
            select(User)
            .filter(User.id == user_id)
        )

        result = db.execute(query)

        return result.scalars().first()
    
    
    @staticmethod
    def get_user_by_username(db: Session, username):
        query = (
            select(User)
            .filter(User.username == username)
        )

        result = db.execute(query)

        return result.scalars().first()
    

    @staticmethod
    def search_users(db: Session, search_request):
        query = select(User)

        if search_request.first_name:
            query = query.filter(User.first_name.ilike('%' + search_request.first_name + '%'))

        if search_request.last_name:
            query = query.filter(User.last_name.ilike('%' + search_request.last_name + '%'))

        if search_request.date_of_birth:
            query = query.filter(User.date_of_birth == search_request.date_of_birth)

        if search_request.role:
            query = query.filter(User.role == search_request.role)

        if search_request.is_active is not None:
            query = query.filter(User.is_active == search_request.is_active)

        result = db.execute(query)

        return result.scalars().all()