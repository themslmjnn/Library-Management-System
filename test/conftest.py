import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base

from src.models.book_inventory_model import BookInventory
from src.models.user_model import User
from src.models.book_model import Book
from models.loaned_book_model import LoanBook

TEST_DB_URL = "postgresql+psycopg2://postgres:musleno@localhost/LMSApplicationTestDB"

engine = create_engine(url=TEST_DB_URL)

TestingSessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    Base.metadata.create_all(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()