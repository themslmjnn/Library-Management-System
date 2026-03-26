from fastapi import APIRouter, status, Depends

from typing import Annotated

from db.database import db_dependency
from src.core.security import user_dependency
from src.schemas.book_schemas import BookResponse1, BookResponse2, BookCreate, BookSearch, BookUpdate, BookUpdateResponse
from src.schemas.book_inventory_schemas import BookInventoryCreate, BookInventoryResponse1, BookInventoryResponse2, BookInventorySearch, BookInventoryUpdate, BookInventoryUpdateResponse
from src.services.book_services import BookService
from src.utils.constants import path_param_int_ge1


router = APIRouter(
    prefix="/books",
    tags=["Books"]
)


@router.post("/add", response_model=BookResponse1, status_code=status.HTTP_201_CREATED)
def add_book(
        db: db_dependency,
        current_user: user_dependency,
        book_request: BookCreate):
    
    return BookService.add_book(db, current_user, book_request)


@router.get("", response_model=list[BookResponse2], status_code=status.HTTP_200_OK)
def get_all_books(db: db_dependency):
    return BookService.get_all_books(db)


@router.get("/search", response_model=list[BookResponse2], status_code=status.HTTP_200_OK)
def search_book(
        db: db_dependency, 
        search_book_request: Annotated[BookSearch, Depends()]):

    return BookService.search_book(db, search_book_request)


@router.put("/{book_id}/update", response_model=BookUpdateResponse, status_code=status.HTTP_200_OK)
def update_book_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        update_request: BookUpdate, 
        book_id: path_param_int_ge1):

    return BookService.update_book_by_id(db, current_user, update_request, book_id)


@router.post("/inventory/add", response_model=BookInventoryResponse1, status_code=status.HTTP_201_CREATED)
def add_inventory(
        db: db_dependency, 
        current_user: user_dependency,
        inventory_request: BookInventoryCreate):

    return BookService.add_inventory(db, current_user, inventory_request)


@router.get("/inventory", response_model=list[BookInventoryResponse2], status_code=status.HTTP_200_OK)
def get_all_inventories(
        db: db_dependency,
        current_user: user_dependency):

    return BookService.get_all_inventories(db, current_user)
    

@router.get("/inventory/search", response_model=list[BookInventoryResponse2], status_code=status.HTTP_200_OK)
def search_inventories(
        db: db_dependency, 
        current_user: user_dependency,
        search_request: Annotated[BookInventorySearch, Depends()]):

    return BookService.search_inventories(db, current_user, search_request)


@router.put("/inventory/{inventory_id}/update/quantity", response_model=BookInventoryResponse2, status_code=status.HTTP_200_OK)
def update_inventory_quantity(
        db: db_dependency, 
        current_user: user_dependency,
        quantity: int, 
        inventory_id: path_param_int_ge1):

    return BookService.update_inventory_quantity_by_id(db, current_user, quantity, inventory_id)


@router.get("/{book_id}", response_model=BookResponse2, status_code=status.HTTP_200_OK)
def get_book_by_id(
        db: db_dependency,
        book_id: path_param_int_ge1):
    
    return BookService.get_book_by_id(db, book_id)


@router.get("/inventory/{inventory_id}", response_model=BookInventoryResponse2, status_code=status.HTTP_200_OK)
def get_inventory_by_id(
        db: db_dependency, 
        current_user: user_dependency,
        inventory_id: path_param_int_ge1):

    return BookService.get_inventory_by_id(db, current_user, inventory_id)