from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.utils.exception_constants import HTTP404, HTTP409


def handle_user_integrity_error(error: IntegrityError) -> None:
    error_str = str(error.orig)

    if "users_username_key" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.USERNAME,
        )
    
    if "users_email_key" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.EMAIL,
        )
    
    if "users_phone_number_key" in error_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=HTTP409.PHONE_NUMBER,
        )
    

def check_unique_title_and_author(error: IntegrityError) -> None:
    if "uix_title_author" in str(error.orig):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=HTTP409.TITLE_OR_AUTHOR,
        )


def check_book_id_fkey_error(error: IntegrityError) -> None:
    if "inventories_book_id_fkey" in str(error.orig):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=HTTP404.BOOK,
        )