from fastapi import APIRouter, Depends, HTTPException, Path, Query
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from typing import Annotated, Optional
from starlette import status
from pydantic_schemas import BookCreate, BookResponse, BookUpdate
from datetime import date

import models


router = APIRouter()

db_dependency = Annotated[Session, Depends(get_db)]

MESSAGE_404 = "Book not found"

@router.get("/books", response_model=list[BookResponse], status_code=status.HTTP_200_OK, tags=["Get Methods"])
async def get_all_books(db: db_dependency): 
    return db.query(models.Books).all()


@router.get("/books/search", response_model=list[BookResponse], status_code=status.HTTP_200_OK, tags=["Search Methods"])
async def search_books(
    db: db_dependency, 
    title: Optional[str] = Query(None, min_length=3),
    author: Optional[str] = Query(None, min_length=3),
    category: Optional[str] = Query(None, min_length=3),
    rating: Optional[float] = Query(None, ge=1, le=5),
    publishing_date: Optional[date] = Query(None)
):

    query = db.query(models.Books)

    if title:
        query = query.filter(func.lower(models.Books.title).contains(title.lower()))

    if author:
        query = query.filter(func.lower(models.Books.author).contains(author.lower()))

    if category:
        query = query.filter(func.lower(models.Books.category).contains(category.lower()))

    if rating is not None:
        query = query.filter(models.Books.rating == rating)

    if publishing_date:
        query = query.filter(models.Books.publishing_date == publishing_date)

    results = query.all()

    if not results:
        raise HTTPException(status_code=404, detail=MESSAGE_404)

    return results


@router.get("/books/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK, tags=["Search Methods"])
async def get_books_by_id(db: db_dependency, book_id: int = Path(ge=1)):
    query_result = db.query(models.Books).filter(models.Books.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail=MESSAGE_404)
    
    return query_result


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Delete Methods"])
async def delete_books_by_id(db: db_dependency, book_id: int = Path(ge=1)):
    query_result = db.query(models.Books).filter(models.Books.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail=MESSAGE_404)
    
    db.delete(query_result)
    db.commit()


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED, tags=["Add Methods"])
async def add_books(db: db_dependency, book_request: BookCreate):
    new_book = models.Books(**book_request.model_dump())

    try:
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
        
        return new_book
    except IntegrityError:
        db.rollback()

        raise HTTPException(status_code=409, detail="Duplicate values are not accepted")
    

@router.put("/books/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK, tags=["Update Methods"])
async def update_books(db: db_dependency, book_request: BookUpdate, book_id: int = Path(ge=1)):
    query_result = db.query(models.Books).filter(models.Books.id == book_id).first()

    if query_result is None:
        raise HTTPException(status_code=404, detail=MESSAGE_404)

    try:
        for field, value in book_request.model_dump().items():
            if value is not None:
                setattr(query_result, field, value)

        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(status_code=409, detail="Duplicate values are not accepted")

    return query_result