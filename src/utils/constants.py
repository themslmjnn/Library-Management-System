from fastapi import Path

from typing import Annotated


MESSAGE_400_PASSWORD = "Incorrect old password"
MESSAGE_401 = "Could not validate user"
MESSAGE_403 = "Accessing denied"
MESSAGE_404_USER = "User(s) not found"
MESSAGE_404_BOOK = "Book(s) not found"
MESSAGE_404_INVENTORY = "Book inventory(s) not found"
MESSAGE_409_DUPLICATE = "Duplicate values are not accepted"
MESSAGE_409_2 = "Username already taken"
MESSAGE_409_3 = "Email already registered"

path_param_int_ge1 = Annotated[int, Path(ge=1)]