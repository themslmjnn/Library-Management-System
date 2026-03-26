from src.core.security import bcrypt_context
from src.repositories.user_repositories import UserRepository


class TokenService:
    @staticmethod
    def authenticate_user(username: str, password: str, db):
        user = UserRepository.get_user_by_username(db, username)

        if not user:
            return False
        
        if not user.is_active:
            return False
        
        if not bcrypt_context.verify(password, user.password_hash):
            return False
        
        return user