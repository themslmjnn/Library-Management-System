from fastapi import FastAPI
from src.auth.router import router as auth_router
from src.user.router_admin import router as user_router_admin
from src.user.router_staff import router as user_router_staff
from src.user.router_public import router as user_router_public

app = FastAPI(title="Library Management System")

app.include_router(auth_router)
app.include_router(user_router_admin)
app.include_router(user_router_staff)
app.include_router(user_router_public)