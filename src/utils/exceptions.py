from fastapi import HTTPException, status

from src.utils.constants import MESSAGE_404_USER, MESSAGE_404_BOOK
from src.utils.constants import MESSAGE_409_USERNAME, MESSAGE_409_EMAIL, MESSAGE_409_TITLE_OR_AUTHOR


def check_unique_username_error(error):
    if "ix_users_username" in str(error.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_USERNAME)


def check_unique_email_error(error):
    if "users_email_address_key" in str(error.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_EMAIL)


def check_unique_title_and_author(error):
    if "uix_title_author" in str(error.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_TITLE_OR_AUTHOR)


def check_book_id_fkey_error(e):
    if "book_inventories_book_id_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MESSAGE_404_BOOK)
    

def check_added_by_fkey_error(e):
    if "book_inventories_added_by_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MESSAGE_404_USER)