from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import mapped_column

str30_ix_non_null = Annotated[str, mapped_column(String(30), index=True, nullable=False)]
int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at_constant = Annotated[
    datetime, 
    mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False),
]
updated_at_constant = Annotated[
    datetime, 
    mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
]