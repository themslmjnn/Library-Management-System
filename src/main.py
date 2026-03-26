from fastapi import FastAPI

from routers import auth_routers, user_routers
from src.routers import admin

app = FastAPI(title="Library Management System v1.0")

app.include_router(auth_routers.router)
app.include_router(admin.router)
app.include_router(user_routers.router)