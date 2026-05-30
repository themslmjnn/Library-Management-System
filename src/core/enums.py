from enum import Enum


class OrderBy(str, Enum):
    asc = "asc"
    desc = "desc"


class BookSortField(str, Enum):
    created_at = "created_at"
    title = "title"
    author = "author"
