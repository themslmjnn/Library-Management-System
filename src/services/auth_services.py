from src.repositories.auth_repositories import UserRepository

class TokenService:
    @staticmethod
    def authenticate_user(username: str, password: str, db, bcrypt_context):
        user = UserRepository.get_user_by_username(db, username)

        if not user:
            return False
        
        if not bcrypt_context.verify(password, user.hash_password):
            return False
        
        return user
    