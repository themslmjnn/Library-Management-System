from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.utils.exception_constants import HTTP404, HTTP409


def handle_user_integrity_error(e: IntegrityError) -> None:
    error_str = str(e.orig).lower()

    if "username" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.USERNAME,
        )
    if "email" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.EMAIL,
        )
    if "phone_number" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.PHONE_NUMBER,
        )
    

def check_unique_title_and_author(error):
    if "uix_title_author" in str(error.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=HTTP409.TITLE_OR_AUTHOR)


def check_book_id_fkey_error(e):
    if "inventories_book_id_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HTTP404.BOOK)
    

def check_added_by_fkey_error(e):
    if "inventories_added_by_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=HTTP404.BOOK)