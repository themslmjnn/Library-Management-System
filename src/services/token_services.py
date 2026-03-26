from jose import jwt

from datetime import datetime, timezone, timedelta

from db.config import settings


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}

    expires = datetime.now(timezone.utc) + expires_delta

    encode.update({'exp': expires})

    return jwt.encode(encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)