from database import Base
from sqlalchemy import Column, Integer, String, Date, Double, UniqueConstraint, Boolean


class Books(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    author = Column(String)
    category = Column(String)
    description = Column(String)
    rating = Column(Double)
    publishing_date = Column(Date)

    __table_args__ = (
        UniqueConstraint('title', 'author', name="uix_title_author"),
    )

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    date_of_birth = Column(Date, nullable=False)
    email_address = Column(String, unique=True, nullable=False)
    hash_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
