from sqlalchemy import String
from sqlalchemy.orm import mapped_column

from typing import Annotated


int_pk = Annotated[int, mapped_column(primary_key=True)]
str_ix_30 = Annotated[str, mapped_column(String(30), nullable=False)]
str_uix_50 = Annotated[str, mapped_column(String(50), unique=True, nullable=False)]