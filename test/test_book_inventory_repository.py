from src.models.book_inventory_model import BookInventory
from src.models.user_model import User, UserRole
from src.models.book_model import Book, Category
from src.repositories.book_inventory_repositories import BookInventoryRepository
from datetime import datetime, date

def test_get_quantity_added(db):
    user = User(
        username="test_username1",
        first_name="t_fn_user1",
        last_name="t_ln_user1",
        date_of_birth=date(2026, 1, 1),
        email_address="t_user1_ea@gmail.com",
        hash_password="123456user1",
        role=UserRole.user,
        is_active=True,
        created_by=None,
        created_at=datetime.now()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    book = Book(
        title="book1",
        author="author1",
        category=Category.fiction,
        description=None,
        rating=4.5,
        publishing_date=date(2026, 10, 10),
        created_at=datetime.now(),
        created_by=user.id
    )

    db.add(book)
    db.commit()
    db.refresh(book)

    new_book_inventory = BookInventory(
        book_id=1,
        added_by=1,
        added_at=datetime.now(),
        quantity_added=50
    )

    db.add(new_book_inventory)
    db.commit()
    db.refresh(new_book_inventory)

    quantity_added = BookInventoryRepository.get_quantity_added(db, new_book_inventory.book_id)

    assert quantity_added is not None
    assert quantity_added == 50