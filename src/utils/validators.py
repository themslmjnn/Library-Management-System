from datetime import date

from src.user.models import UserRole


def validate_password(password: str) -> str:
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        raise ValueError("Password must contain at least one special character.")
    return password


def validate_date_of_birth(birth_date: str) -> date:
    today = date.today()
        
    if birth_date >= today:
        raise ValueError("Date of birth must be in the past.")
        
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age < 13:
        raise ValueError("User must be at least 13 years old.")
    if age > 120:
        raise ValueError("Please enter a valid date of birth.")
        
    return birth_date


def validate_email(email: str) -> str:
    if email.split('@')[-1] not in ("gmail.com", "mail.ru", "outlook.com", "yahoo.com", "icloud.com"):
        raise ValueError("Email with the following domain is not accepted")
    
    return email


def validate_role(role: UserRole) -> UserRole:
    if role == UserRole.system_admin:
        raise ValueError("Cannot assign system_admin role")
    
    return role