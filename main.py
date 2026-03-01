from fastapi import FastAPI

from src.routers import admin, auth, core

app = FastAPI(title="Library Management System v1.0")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(core.router)