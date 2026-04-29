import re
from datetime import date

from pydantic import PydanticCustomError


def validate_password(password: str) -> str:
    if not any(c.isupper() for c in password):
        raise PydanticCustomError(
            "password_no_uppercase",
            "Password must contain at least one uppercase letter",
        )
    if not any(c.isdigit() for c in password):
        raise PydanticCustomError(
            "password_no_digit",
            "Password must contain at least one digit",
        )
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise PydanticCustomError(
            "password_no_special_character",
            "Password must contain at least one special character",
        )
    
    return password


def validate_date_of_birth(birth_date: date) -> date:
    today = date.today()

    if birth_date >= today:
        raise PydanticCustomError(
            "date_of_birth_not_in_past",
            "Date of birth must be in the past",
        )

    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    if age < 13:
        raise PydanticCustomError(
            "date_of_birth_too_young",
            "User must be at least 13 years old",
        )
    if age > 120:
        raise PydanticCustomError(
            "date_of_birth_invalid",
            "Please enter a valid date of birth",
        )

    return birth_date


# PHONE NUMBER

# Accepts:
#   +992 123 456 789
#   +15550001234
#   +44-20-7946-0958
#   (123) 456-7890       ← US local format
#   123 456 7890
# Rejects:
#   letters, symbols other than +, -, (, ), space
#   fewer than 7 digits or more than 15 digits (ITU-T E.164 standard)

_PHONE_RE = re.compile(r"^[+\d][\d\s\-().]{5,19}$")
_DIGIT_RE = re.compile(r"\d")

def validate_phone_number(phone: str) -> str:
    phone = phone.strip()

    if not _PHONE_RE.match(phone):
        raise PydanticCustomError(
            "phone_invalid_format",
            "Phone number contains invalid characters",
        )

    digit_count = len(_DIGIT_RE.findall(phone))

    if digit_count < 7:
        raise PydanticCustomError(
            "phone_too_short",
            "Phone number must contain at least 7 digits",
        )
    if digit_count > 15:
        raise PydanticCustomError(
            "phone_too_long",
            "Phone number must not exceed 15 digits",
        )

    return phone


def validate_publishing_date(publishing_date: date) -> date:
    if publishing_date > date.today():
        raise PydanticCustomError(
            "publishing_date_in_future",
            "Publishing date must be in the past",
        )
    return publishing_date