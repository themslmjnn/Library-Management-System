from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import generate_account_activation_code, generate_invite_token, hash_password
from src.user.models import UserRole, User
from datetime import datetime, timedelta, timezone, date

from src.user.repository import UserRepositoryBase


async def make_user(
    db: AsyncSession,
    *,
    role: UserRole = UserRole.guest,
    is_active: bool = True,
    email: str | None = None,
    phone_number: str | None = None,
    username: str | None = None,
    password: str = "Test123!",
    has_password: bool = True,
    created_by: int | None = None,
) -> User:
    
    _id = int(datetime.now(timezone.utc).timestamp() * 1000) % 100000

    new_user = User(
        username=username or f"user_{_id}",
        first_name="Test",
        last_name="User",
        date_of_birth=date(1990, 1, 1),
        email=email or f"user_{_id}@gmail.com",
        phone_number=phone_number or f"+1555{_id:07d}",
        password_hash=hash_password(password) if has_password else None,
        role=role,
        is_active=is_active,
        created_by=created_by,
    )

    UserRepositoryBase.add_user(db, new_user)

    await db.commit()
    await db.refresh(new_user)

    return new_user

async def make_system_admin(db: AsyncSession, **kwargs) -> User:
    return await make_user(db, role=UserRole.system_admin, **kwargs)


async def make_library_admin(db: AsyncSession, **kwargs) -> User:
    return await make_user(db, role=UserRole.library_admin, **kwargs)

async def make_receptionist(db: AsyncSession, **kwargs) -> User:
    return await make_user(db, role=UserRole.receptionist, **kwargs)

async def make_member(db: AsyncSession, **kwargs) -> User:
    return await make_user(db, role=UserRole.member, **kwargs)

async def make_guest(db: AsyncSession, **kwargs) -> User:
    return await make_user(db, role=UserRole.guest, **kwargs)


async def make_invited_user(
    db: AsyncSession,
    *,
    role: UserRole = UserRole.guest,
    created_by: int | None = None,
) -> tuple[User, str]:

    raw_token, hashed_token = generate_invite_token()
    _id = int(datetime.now(timezone.utc).timestamp() * 1000) % 100000

    new_user = User(
        username=f"invited_{_id}",
        first_name="Invited",
        last_name="User",
        date_of_birth=date(1995, 6, 15),
        email=f"invited_{_id}@gmail.com",
        phone_number=f"+1444{_id:07d}",
        password_hash=None,
        role=role,
        is_active=False,
        invite_token_hash=hashed_token,
        invite_token_expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        created_by=created_by,
    )

    UserRepositoryBase.add_user(db, new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user, raw_token



async def make_user_with_activation_code(
    test_db: AsyncSession,
    **kwargs,
) -> tuple[User, str]:
    """Create a publicly registered user with a pending activation code."""
    raw_code, hashed_code = generate_account_activation_code()
    _id = int(datetime.now(timezone.utc).timestamp() * 1000) % 100000

    user = User(
        username=f"public_{_id}",
        first_name="Public",
        last_name="User",
        date_of_birth=date(1995, 3, 20),
        email=kwargs.get("email", f"public_{_id}@gmail.com"),
        phone_number=kwargs.get("phone_number", f"+1333{_id:07d}"),
        password_hash=hash_password("Register123!"),
        role=UserRole.guest,
        is_active=False,
        account_activation_code_hash=hashed_code,
        account_activation_code_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    UserRepositoryBase.add_user(test_db, user)
    await test_db.commit()
    await test_db.refresh(user)
    return user, raw_code