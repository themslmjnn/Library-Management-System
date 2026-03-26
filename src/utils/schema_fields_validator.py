from datetime import date


def _validate_password(password: str) -> str:
    if not any(symbol.isupper() for symbol in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(symbol.isdigit() for symbol in password):
        raise ValueError("Password must contain at least one digit")
    if not any(symbol in "!@#$%^&*()_+-=[]{}|;:,.<>?" for symbol in password):
        raise ValueError("Password must contain at least one special character")
    
    return password


def _validate_date_of_birth(date_of_birth: date) -> date:
    today = date.today()
        
    if date_of_birth >= today:
        raise ValueError("Date of birth must be in the past")
        
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

    if not 12 <= age <= 100:
        raise ValueError("Birth date range must be between 12 and 100")
        
    return date_of_birth


def _validate_email_address(email_address: str) -> str:
    if email_address.split('@')[-1] not in ("gmail.com", "mail.ru", "outlook.com", "yahoo.com", "icloud.com"):
        raise ValueError("Email with the following domain is not accepted")
    
    return email_address


def _validate_publishing_date(publishing_date: date) -> date:
    today = date.today()

    if publishing_date > today:
        raise ValueError("Publishing date must be in the past")

    return publishing_date