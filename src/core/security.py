import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.auth.schemas import CreateAccessTokenRequest, CreateRefreshTokenRequest
from src.core.config import settings
from src.utils.exception_constants import HTTP401

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return bcrypt_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def generate_invite_token() -> tuple[str, str]:
    raw_invite_token = secrets.token_urlsafe(32)
    hashed_invite_token = hashlib.sha256(raw_invite_token.encode()).hexdigest()

    return raw_invite_token, hashed_invite_token

def verify_invite_token(raw_invite_token: str, hashed_invite_token: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(raw_invite_token.encode()).hexdigest(), 
        hashed_invite_token,
    )


def generate_account_activation_code() -> tuple[str, str]:
    raw_activation_code = secrets.token_hex(8)
    hashed_activation_code = hashlib.sha256(raw_activation_code.encode()).hexdigest()

    return raw_activation_code, hashed_activation_code

def verify_account_activation_code(raw_activation_code: str, hashed_activation_code: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(raw_activation_code.encode()).hexdigest(), 
        hashed_activation_code,
    )


def create_access_token(payload: CreateAccessTokenRequest) -> str:
    payload = {
        "sub": str(payload.user_id),
        "role": payload.role,
        "version": payload.access_token_version,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES
        ),
    }

    return jwt.encode(
        payload, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.ALGORITHM,
    )

def decode_access_token(access_token: str) -> dict:
    try:
        payload = jwt.decode(
            access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if payload.get("type") != "access":
            raise ValueError(HTTP401.INVALID_TOKEN_TYPE)
        
        return payload
    except JWTError:
        raise ValueError(HTTP401.EXPIRED_ACCESS_TOKEN)
    

def create_refresh_token(payload: CreateRefreshTokenRequest) -> tuple[str, str]:
    raw_refresh_token = jwt.encode(
        {
            "sub": str(payload.user_id),
            "family": payload.family,
            "type": "refresh",
            "jti": secrets.token_urlsafe(16),
            "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRES_DAYS),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    hashed_refresh_token =  hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    return raw_refresh_token, hashed_refresh_token

def decode_refresh_token(refresh_token: str) -> dict:
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if payload.get("type") != "refresh":
            raise ValueError(HTTP401.INVALID_TOKEN_TYPE)
        
        return payload
    
    except JWTError:
        raise ValueError(HTTP401.EXPIRED_REFRESH_TOKEN)
    
def verify_refresh_token(raw_refresh_roken: str, hashed_refresh_token: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(raw_refresh_roken.encode()).hexdigest(), 
        hashed_refresh_token,
    )