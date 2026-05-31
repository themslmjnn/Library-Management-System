from enum import Enum


class UserRole(str, Enum):
    system_admin = "system_admin"
    library_admin = "library_admin"
    receptionist = "receptionist"
    member = "member"
    guest = "guest"


class UserSortField(str, Enum):
    created_at = "created_at"
    first_name = "first_name"
    last_name = "last_name"


class BookCategory(str, Enum):
    self_improvement = "self improvement"
    fiction = "fiction"
    stories = "stories"
    history = "history"
    science = "science"
    others = "others"


class BookSortField(str, Enum):
    created_at = "created_at"
    title = "title"
    author = "author"
