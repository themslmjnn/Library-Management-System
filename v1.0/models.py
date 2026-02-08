from database import Base
from sqlalchemy import Column, Integer, String, Date, Double, UniqueConstraint


class Book(Base):
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

