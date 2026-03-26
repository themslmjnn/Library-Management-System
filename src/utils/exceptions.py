from fastapi import HTTPException, status

from src.utils.constants import MESSAGE_404_USER, MESSAGE_404_BOOK, MESSAGE_409_1, MESSAGE_409_2, MESSAGE_409_3


def check_unique_username_error(e):
    if "ix_users_username" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_2)


def check_unique_email_error(e):
    if "ix_users_email_address" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_3)
    

def check_uix_title_deadline_error(e):
    if "uix_title_deadline" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MESSAGE_409_1)
    

def check_book_id_fkey_error(e):
    if "book_inventories_book_id_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MESSAGE_404_BOOK)
    

def check_added_by_fkey_error(e):
    if "book_inventories_added_by_fkey" in str(e.orig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MESSAGE_404_USER)
