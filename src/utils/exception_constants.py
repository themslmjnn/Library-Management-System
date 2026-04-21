from typing import Annotated

from fastapi import Path

# --- Path Parameters ---
path_param_int_ge1 = Annotated[int, Path(ge=1)]

# --- HTTP 400 Bad Request ---
class HTTP400:
    INCORRECT_PASSWORD = "Incorrect old password"
    INVITE_TOKEN_USED = "Account already activated or was never invited"
    EXPIRED_INVITE_TOKEN = "Invite token has expired"
    INVALID_INVITE_TOKEN = "Invalid invite token"
    INVALID_ACTIVATION_CODE = "Invalid activation code"
    EXPIRED_ACTIVATION_CODE = "Expired activation code"


# --- HTTP 401 Unauthorized ---
class HTTP401:
    INVALID_CREDENTIALS = "Invalid credentials"
    ACCOUNT_NOT_ACTIVATED = "Account has not been activated yet"
    EXPIRED_REFRESH_TOKEN = "Expired refresh token"
    INVALID_REFRESH_TOKEN = "Invalid refresh token"
    INVALID_ACCESS_TOKEN = "Invalid access token"
    INVALID_TOKEN_TYPE = "Invalid token type"


# --- HTTP 403 Forbidden ---
class HTTP403:
    ACCESS_DENIED = "Access denied"
    ACCOUNT_DEACTIVATED = "Your account has been deactivated"


# --- HTTP 404 Not Found ---
class HTTP404:
    USER = "User not found"


# --- HTTP 409 Conflict ---
class HTTP409:
    USERNAME = "Username already taken."
    EMAIL = "Email already taken."
    PHONE_NUMBER = "Phone number already taken."