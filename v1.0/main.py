from fastapi import FastAPI
from database import engine
from routers import auth, books

import models


app = FastAPI(title="Library Management System v1.0")

app.include_router(auth.router)
app.include_router(books.router)

models.Base.metadata.create_all(bind=engine)