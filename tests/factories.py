import itertools
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import CreateRefreshTokenRequest
from src.book.models import Book
from src.book.repository import BookRepository
from src.core.security import (
    create_refresh_token,
    generate_account_activation_code,
    generate_invite_token,
    hash_password,
)
from src.inventory.models import Inventory
from src.inventory.repository import InventoryRepository
from src.user.models import User, UserActivation, UserRole, UserSession
from src.user.repository import UserRepositoryBase
from tests.constants import CORRECT_PASSWORD, DEFAULT_PASSWORD, NEW_PASSWORD

_counter = itertools.count(1)


def _next() -> int:
    return next(_counter)


async def make_user(
    test_db: AsyncSession,
    *,
    role: UserRole = UserRole.guest,
    is_active: bool = True,
    email: str | None = None,
    phone_number: str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    password: str = DEFAULT_PASSWORD,
    has_password: bool = True,
    created_by: int | None = None,
) -> User:

    n = _next()

    new_user = User(
        username=username or f"user_{n}",
        first_name=first_name or "test_fname",
        last_name=last_name or "test_lname",
        date_of_birth=date(2000, 1, 1),
        email=email or f"user_{n}@gmail.com",
        phone_number=phone_number or f"+992 000 {n:07d}",
        password_hash=hash_password(password) if has_password else None,
        role=role,
        is_active=is_active,
        created_by=created_by,
    )

    UserRepositoryBase.add_entity(test_db, new_user)

    await test_db.flush()

    new_user_activation = UserActivation(
        user_id=new_user.id,
    )

    new_user_session = UserSession(
        user_id=new_user.id,
    )

    UserRepositoryBase.add_entity(test_db, new_user_activation)
    UserRepositoryBase.add_entity(test_db, new_user_session)

    await test_db.commit()
    await test_db.refresh(new_user)

    return new_user


async def make_system_admin(test_db: AsyncSession, **kwargs) -> User:
    return await make_user(test_db, role=UserRole.system_admin, **kwargs)


async def make_library_admin(test_db: AsyncSession, **kwargs) -> User:
    return await make_user(test_db, role=UserRole.library_admin, **kwargs)


async def make_receptionist(test_db: AsyncSession, **kwargs) -> User:
    return await make_user(test_db, role=UserRole.receptionist, **kwargs)


async def make_member(test_db: AsyncSession, **kwargs) -> User:
    return await make_user(test_db, role=UserRole.member, **kwargs)


async def make_guest(test_db: AsyncSession, **kwargs) -> User:
    return await make_user(test_db, role=UserRole.guest, **kwargs)


async def make_invited_user(
    test_db: AsyncSession,
    *,
    role: UserRole = UserRole.guest,
    created_by: int | None = None,
) -> tuple[User, str]:

    raw_invite_token, hashed_invite_token = generate_invite_token()
    n = _next()

    new_user = User(
        username=f"invited_{n}",
        first_name="Invited",
        last_name="User",
        date_of_birth=date(1995, 6, 15),
        email=f"invited_{n}@gmail.com",
        phone_number=f"+1444{n:07d}",
        password_hash=None,
        role=role,
        is_active=False,
        created_by=created_by,
    )

    UserRepositoryBase.add_entity(test_db, new_user)

    await test_db.flush()

    new_user_activation = UserActivation(
        user_id=new_user.id,
        invite_token_hash=hashed_invite_token,
        invite_token_expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )

    new_user_session = UserSession(
        user_id=new_user.id,
    )

    UserRepositoryBase.add_entity(test_db, new_user_activation)
    UserRepositoryBase.add_entity(test_db, new_user_session)

    await test_db.commit()
    await test_db.refresh(new_user)

    return new_user, raw_invite_token


async def make_user_with_activation_code(
    test_db: AsyncSession,
    **kwargs,
) -> tuple[User, str]:

    raw_code, hashed_code = generate_account_activation_code()
    n = _next()

    new_user = User(
        username=f"public_{n}",
        first_name="Public",
        last_name="User",
        date_of_birth=date(1995, 3, 20),
        email=kwargs.get("email", f"public_{n}@gmail.com"),
        phone_number=kwargs.get("phone_number", f"+1333{n:07d}"),
        password_hash=hash_password(NEW_PASSWORD),
        role=UserRole.guest,
        is_active=False,
    )

    UserRepositoryBase.add_entity(test_db, new_user)

    await test_db.flush()

    new_user_activation = UserActivation(
        user_id=new_user.id,
       account_activation_code_hash=hashed_code,
        account_activation_code_expires_at=datetime.now(timezone.utc)
        + timedelta(days=1),
    )

    new_user_session = UserSession(
        user_id=new_user.id,
    )

    UserRepositoryBase.add_entity(test_db, new_user_activation)
    UserRepositoryBase.add_entity(test_db, new_user_session)

    await test_db.commit()
    await test_db.refresh(new_user)

    return new_user, raw_code


async def make_user_with_refresh_token(test_db: AsyncSession):
    user = await make_member(
        test_db,
        password=CORRECT_PASSWORD,
    )

    raw_refresh_token, hashed_refresh_token = create_refresh_token(
        CreateRefreshTokenRequest(
            user_id=user.id,
            family="test_family_abc",
        )
    )
    user_session = await UserRepositoryBase.get_user_with_session(test_db, user.id)
    user_session.session.refresh_token_hash = hashed_refresh_token
    user_session.session.refresh_token_family = "test_family_abc"
    user_session.session.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    await test_db.commit()

    return user, raw_refresh_token


async def make_book(
    test_db: AsyncSession,
    *,
    title: str | None = None,
    author: str | None = None,
    category: str = "others",
    description: str | None = None,
    publishing_date: date = date(2000, 1, 1),
    created_by: int,
) -> Book:
    n = _next()

    book = Book(
        title=title or f"Book_{n}",
        author=author or f"Author_{n}",
        category=category,
        description=description,
        publishing_date=publishing_date,
        created_by=created_by,
    )

    BookRepository.add_book(test_db, book)

    await test_db.commit()
    await test_db.refresh(book)

    return book


async def make_inventory(
    test_db: AsyncSession,
    *,
    book_id: int,
    quantity: int = 5,
    added_by: int,
) -> Inventory:
    inventory = Inventory(
        book_id=book_id,
        quantity=quantity,
        added_by=added_by,
    )

    InventoryRepository.add_inventory(test_db, inventory)

    await test_db.commit()
    await test_db.refresh(inventory)

    return inventory
