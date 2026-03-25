from datetime import date


def _validate_password(v: str) -> str:
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
        raise ValueError("Password must contain at least one special character.")
    return v


def _validate_date_of_birth(v: str) -> date:
    today = date.today()
        
    if v >= today:
        raise ValueError("Date of birth must be in the past.")
        
    age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
    if age < 13:
        raise ValueError("User must be at least 13 years old.")
    if age > 120:
        raise ValueError("Please enter a valid date of birth.")
        
    return v


def _validate_email(v: str) -> str:
    if v.split('@')[-1] not in ("gmail.com", "mail.ru", "outlook.com", "yahoo.com", "icloud.com"):
        raise ValueError("Email with the following domain is not accepted")
    
    return v


def _validate_publishing_date(v: str) -> date:
    today = date.today()
        
    if v >= today:
        raise ValueError("Date of birth must be in the past.")