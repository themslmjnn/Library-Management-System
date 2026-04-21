from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from src.utils.exception_constants import HTTP409

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
    


