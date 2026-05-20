def book_detail_key(book_id: int) -> str:
    return f"books:detail:{book_id}"


def book_detail_key_public(book_id: int) -> str:
    return f"books:detail:{book_id}:public"


def inventory_detail_key(inventory_id: int) -> str:
    return f"inventories:detail:{inventory_id}"


def user_detail_key_admin(user_id: int) -> str:
    return f"users:detail:{user_id}:admin"


def user_detail_key_staff(user_id: int) -> str:
    return f"users:detail:{user_id}:staff"


def user_detail_key_self(user_id: int) -> str:
    return f"users:detail:{user_id}:self"


def loan_detail_key(loan_id: int) -> str:
    return f"loans:detail:{loan_id}"


def access_token_version_key(user_id: int) -> str:
    return f"user:token_version:{user_id}"
