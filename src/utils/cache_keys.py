def book_detail_key(book_id: int) -> str:
    return f"books:detail:{book_id}"


def inventory_detail_key(inventory_id: int) -> str:
    return f"inventories:detail:{inventory_id}"