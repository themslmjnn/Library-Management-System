from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from jose import jwt, JWTError
from passlib.context import CryptContext

from typing import Annotated

from db.config import settings
from src.utils.constants import MESSAGE_401


oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        username: str = payload.get('sub')
        user_id: str = payload.get('id')
        user_role: str = payload.get('role')

        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MESSAGE_401)
        
        return {"username": username, "id": user_id, "role": user_role}
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MESSAGE_401)


user_dependency = Annotated[dict, Depends(get_current_user)]


def hash_password(password) -> str:
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password, message) -> None:
    if not bcrypt_context.verify(plain_password, hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)