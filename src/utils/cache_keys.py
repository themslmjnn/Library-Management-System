def book_detail_key(book_id: int) -> str:
    return f"books:detail:{book_id}"


def inventory_detail_key(inventory_id: int) -> str:
    return f"inventories:detail:{inventory_id}"


def user_detail_key(user_id: int) -> str:
    return f"users:detail:{user_id}"