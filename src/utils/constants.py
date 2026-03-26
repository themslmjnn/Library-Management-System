from fastapi import Path

from typing import Annotated


MESSAGE_400_PASSWORD = "Incorrect old password"
MESSAGE_400_BOOK = "Book is already returned"

MESSAGE_401_VALIDATE = "Could not validate user"

MESSAGE_403_FORBIDDEN = "Accessing denied"

MESSAGE_404_USER = "User(s) not found"
MESSAGE_404_BOOK = "Book(s) not found"
MESSAGE_404_BOOK_NOT_AVAILABLE = "Books not availabe"
MESSAGE_404_INVENTORY = "Book inventory(s) not found"
MESSAGE_404_LOAN = "Loan(s) not found"

MESSAGE_409_DUPLICATE = "Duplicate values are not accepted"
MESSAGE_409_USERNAME = "Username already taken"
MESSAGE_409_EMAIL = "Email already registered"
MESSAGE_409_TITLE_OR_AUTHOR = "Duplicate title or author"

path_param_int_ge1 = Annotated[int, Path(ge=1)]