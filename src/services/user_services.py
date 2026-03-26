from sqlalchemy.exc import IntegrityError

from src.models.user_model import User, UserRole
from src.repositories.user_repositories import UserRepository
from src.core.security import hash_password, verify_password
from src.utils.exceptions import check_unique_username_error, check_unique_email_error
from src.utils.helpers import require_admin, require_user, require_admin_or_owner
from src.utils.helpers import ensure_exists, update_object
from src.utils.constants import MESSAGE_404_USER, MESSAGE_400_PASSWORD


class UserService:
    @staticmethod
    def register_user_public(db, user_request):
        new_user = User(
            username=user_request.username,
            first_name=user_request.first_name.title(),
            last_name=user_request.last_name.title(),
            date_of_birth=user_request.date_of_birth,
            email_address=user_request.email_address,
            password_hash=hash_password(user_request.password),
            role=UserRole.user,
            is_active=True
        )

        try:
            UserRepository.register_user(db, new_user)

            db.commit()
            db.refresh(new_user)

            return new_user
        
        except IntegrityError as e:
            db.rollback()

            check_unique_username_error(e)

            check_unique_email_error(e)
                
            raise

    
    @staticmethod
    def register_user_admin(db, current_user, user_request):
        require_admin(current_user)

        new_user = User(
            username=user_request.username,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            date_of_birth=user_request.date_of_birth,
            email_address=user_request.email_address,
            password_hash=hash_password(user_request.password),
            role=user_request.role,
            is_active=True,
            created_by=current_user["id"]
        )

        try:
            UserRepository.register_user(db, new_user)

            db.commit()
            db.refresh(new_user)

            return new_user
        
        except IntegrityError as e:
            db.rollback()

            check_unique_username_error(e)

            check_unique_email_error(e)
                
            raise
    

    @staticmethod
    def get_all_users(db, current_user):
        require_admin(current_user)

        return UserRepository.get_all_users(db)
    

    @staticmethod
    def search_users(db, current_user, users_request):
        require_admin(current_user)

        return UserRepository.search_users(db, users_request)
    

    @staticmethod
    def get_user_by_id_admin(db, current_user, user_id):
        require_admin(current_user)

        user = UserRepository.get_user_by_id(db, user_id)
        ensure_exists(user, MESSAGE_404_USER)

        return user
    

    @staticmethod
    def get_user_by_id_public(db, current_user, user_id):
        require_user(current_user, user_id)

        user = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user, MESSAGE_404_USER)

        return user
    

    @staticmethod
    def delete_user_by_id(db, current_user, user_id):
        require_admin_or_owner(current_user, user_id)

        user = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user, MESSAGE_404_USER)
        
        user.is_active = False

        db.commit()


    @staticmethod
    def activate_user_account(db, current_user, user_id):
        require_admin(current_user)
        
        user = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user, MESSAGE_404_USER)
        
        user.is_active = True

        db.commit()


    @staticmethod
    def update_user_info_admin(db, current_user, user_id, user_request):
        require_admin(current_user)

        user = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user, MESSAGE_404_USER)

        try:
            update_object(user, user_request)

            db.commit()

            return user
        
        except IntegrityError as e:
            db.rollback()

            check_unique_username_error(e)

            check_unique_email_error(e)
                
            raise
    

    @staticmethod
    def update_user_info_public(db, current_user, user_id, user_request):
        require_user(current_user, user_id)

        user = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user, MESSAGE_404_USER)

        try:
            update_object(user, user_request)

            db.commit()

            return user
        
        except IntegrityError as e:
            db.rollback()

            check_unique_username_error(e)

            check_unique_email_error(e)

            raise
    

    @staticmethod
    def update_user_password_public(db, current_user, user_id, user_password_request):
        require_user(current_user, user_id)

        user_model = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user_model, MESSAGE_404_USER)
        
        verify_password(user_password_request.old_password, user_model.password_hash, MESSAGE_400_PASSWORD)
        
        user_model.password_hash = hash_password(user_password_request.new_password)

        db.commit()


    @staticmethod
    def update_user_password_admin(db, current_user, user_id, user_password_request):
        require_admin(current_user)
        
        user_model = UserRepository.get_user_by_id(db, user_id)

        ensure_exists(user_model, MESSAGE_404_USER)

        user_model.password_hash = hash_password(user_password_request.new_password)

        db.commit()