from sqlalchemy.exc import IntegrityError

from src.utils.exception_constants import HTTP404, HTTP409


# BASE
class AppException(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


# AUTH
class InvalidCredentialsError(AppException):
    pass

class AccountLockedError(AppException):
    pass

class AccountInactiveError(AppException):
    pass

class InvalidInviteTokenError(AppException):
    pass

class ExpiredInviteTokenError(AppException):
    pass

class InvalidRefreshTokenError(AppException):
    pass

class ExpiredRefreshTokenError(AppException):
    pass

class InvalidActivationCodeError(AppException):
    pass

class ExpiredActivationCodeError(AppException):
    pass


# USER
class UserNotFoundError(AppException):
    pass

class UserAlreadyActiveError(AppException):
    pass

class UserAlreadyInactiveError(AppException):
    pass

class CannotCreateSystemAdminError(AppException):
    pass

class CannotAssignSystemRoleError(AppException):
    pass

class IncorrectPasswordError(AppException):
    pass


# BOOK
class BookNotFoundError(AppException):
    pass

class BookNotAvailableError(AppException):
    pass

class BookAlreadyExistsError(AppException):
    pass


# INVENTORY
class InventoryNotFoundError(AppException):
    pass


# LOAN
class LoanNotFoundError(AppException):
    pass

class LoanAlreadyReturnedError(AppException):
    pass

class UserAlreadyHasActiveLoanError(AppException):
    pass


# INTEGRITY ERROR HANDLERS
def handle_user_integrity_error(error: IntegrityError) -> None:
    error_str = str(error.orig)

    if "users_username_key" in error_str:
        raise AppException(HTTP409.USERNAME)
    
    if "users_email_key" in error_str:
        raise AppException(HTTP409.EMAIL)
    
    if "users_phone_number_key" in error_str:
        raise AppException(HTTP409.PHONE_NUMBER)
    

def check_unique_title_and_author(error: IntegrityError) -> None:
    if "uix_title_author" in str(error.orig):
        raise BookAlreadyExistsError(HTTP409.TITLE_OR_AUTHOR)


def check_book_id_fkey_error(error: IntegrityError) -> None:
    if "inventories_book_id_fkey" in str(error.orig):
        raise BookNotFoundError(HTTP404.BOOK)
    

def handle_loan_integrity_error(e: IntegrityError) -> None:
    raise AppException("Loan could not be created due to a conflict")