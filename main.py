from fastapi import FastAPI
from routers import loan_books
from src.routers import auth, books, returning_books

app = FastAPI(title="Library Management System v1.0")

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(loan_books.router)
app.include_router(returning_books.router)