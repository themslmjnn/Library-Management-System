from fastapi import FastAPI, Depends, HTTPException, Path, Query
from database import engine, get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import Annotated, Optional
from starlette import status
from pydantic_schemas import BookCreate, BookResponse
from datetime import date

import models


app = FastAPI(title="Library Management System v1.0")

models.Base.metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]



@app.get("/books", response_model=list[BookResponse], status_code=status.HTTP_200_OK, tags=["Get Books"])
async def get_all_books(db: db_dependency):
    query_result = db.query(models.Book).all()
    
    return query_result


@app.get("/books/search", response_model=list[BookResponse], status_code=status.HTTP_200_OK, tags=["Search Books"])
async def search_books(
    db: db_dependency,
    title: Optional[str] = Query(None, min_length=3),
    author: Optional[str] = Query(None, min_length=3),
    category: Optional[str] = Query(None, min_length=3),
    rating: Optional[float] = Query(None, ge=1, le=5),
    publishing_date: Optional[date] = Query(None)):

    query = db.query(models.Book)

    if title:
        query = query.filter(func.lower(models.Book.title).contains(title.lower()))

    if author:
        query = query.filter(func.lower(models.Book.author).contains(author.lower()))

    if category:
        query = query.filter(func.lower(models.Book.category).contains(category.lower()))

    if rating is not None:
        query = query.filter(models.Book.rating == rating)

    if publishing_date:
        query = query.filter(models.Book.publishing_date == publishing_date)

    results = query.all()

    if not results:
        raise HTTPException(status_code=404, detail="No books found")

    return results


@app.get("/books/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK, tags=["Search Books"])
async def get_books_by_id(db: db_dependency, book_id: int = Path(ge=1)):
    query_result = db.query(models.Book).filter(models.Book.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return query_result


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Delete Books"])
async def delete_books_by_id(db: db_dependency, book_id: int = Path(ge=1)):
    query_result = db.query(models.Book).filter(models.Book.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(query_result)
    db.commit()


@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED, tags=["Add Books"])
async def add_books(db: db_dependency, book_request: BookCreate):
    new_book = models.Book(**book_request.model_dump())

    try:
        db.add(new_book)
        db.commit()

        return new_book
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate values are not accepted")
    

@app.put("/books/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK, tags=["Update Books"])
async def update_books(db: db_dependency, book_request: BookCreate, book_id: int = Path(ge=1)):
    query_result = db.query(models.Book).filter(models.Book.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        for field, value in book_request.model_dump().items():
            setattr(query_result, field, value)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate values are not accepted")

    return query_result