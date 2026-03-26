import pytest

from repositories.user_repositories import UserRepository
from src.models.user_model import User, UserRole

from datetime import date
from contextlib import nullcontext as does_not_raise


@pytest.mark.parametrize(
        "new_user, result, expectation",
        [
            (
                {
                    "username": "testuser",
                    "first_name": "Test",
                    "last_name": "User",
                    "date_of_birth": date(2000, 1, 1),
                    "email_address": "test@test.com",
                    "hash_password": "hashed",
                    "role": UserRole.user,
                    "is_active": True
                }, 
                "testuser", 
                does_not_raise()
            ),
            (
                {
                    "username": "testuser2",
                    "first_name": "Test",
                    "last_name": "User",
                    "date_of_birth": date(2001, 2, 2),
                    "email_address": "test2@test.com",
                    "hash_password": "hashed",
                    "role": UserRole.user,
                    "is_active": True
                }, 
                "testuser2", 
                does_not_raise()
            ),
        ]
)

def test_get_user_by_id(db, new_user, result, expectation):
    with expectation:
        new_user = User(**new_user)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        user = UserRepository.get_user_by_id(db, new_user.id)

        assert user is not None
        assert user.username == result