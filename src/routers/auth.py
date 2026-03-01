from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from passlib.context import CryptContext
from starlette import status
from typing import Annotated
from datetime import timedelta

from db.database import get_db
from src.schemas.token_schemas import Token
from src.services.auth_services import TokenService
from src.services.token_services import create_access_token


router = APIRouter(
    tags=["Auth"]
)

db_dependency = Annotated[Session, Depends(get_db)]

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

MESSAGE_404 = "User not found"
MESSAGE_401 = "Could not validate user"


@router.post("/auth/token", response_model=Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = TokenService.authenticate_user(form_data.username, form_data.password, db, bcrypt_context)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MESSAGE_401)
    
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=20))

    return {"access_token": token, "token_type": "bearer"}