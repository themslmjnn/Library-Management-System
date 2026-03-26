from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from typing import Annotated
from datetime import timedelta

from db.database import db_dependency
from src.schemas.token_schemas import Token
from src.services.auth_services import TokenService
from src.services.token_services import create_access_token
from src.utils.constants import MESSAGE_401


router = APIRouter(
    tags=["Auth"]
)


@router.post("/auth/token", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = TokenService.authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MESSAGE_401)
    
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=20))

    return {"access_token": token, "token_type": "bearer"}