from enum import Enum


class UserRole(str, Enum):
    system_admin = "system_admin"
    library_admin = "library_admin"
    receptionist = "receptionist"
    member = "member"
    guest = "guest"


class BookCategory(str, Enum):
    self_improvement = "self improvement"
    fiction = "fiction"
    stories = "stories"
    history = "history"
    science = "science"
    others = "others"
