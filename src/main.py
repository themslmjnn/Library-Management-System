from fastapi import FastAPI

from src.routers import auth_routers, user_routers, book_routers, loaned_book_routers

app = FastAPI(title="Library Management System v1.0")

app.include_router(auth_routers.router)
app.include_router(user_routers.router)
app.include_router(book_routers.router)
app.include_router(loaned_book_routers.router)