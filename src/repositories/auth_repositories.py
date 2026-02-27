from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user_model import Users


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
            select(Users)
            .filter(Users.id == user_id)
        )

        result = db.execute(query)

        return result.scalar().first()
    
    
    @staticmethod
    def get_all_users(db: Session):
        query = select(Users)

        result = db.execute(query)

        return result.scalars().all()