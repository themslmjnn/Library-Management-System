from fastapi import APIRouter, Depends, Path, HTTPException
from pydantic_schemas import UserCreate, UserResponse
from starlette import status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from database import get_db

import models


router = APIRouter()

db_dependency = Annotated[Session, Depends(get_db)]


@router.get("/auth", response_model=list[UserResponse], status_code=status.HTTP_200_OK, tags=["Get Methods"])
async def get_all_users(db: db_dependency):
    return db.query(models.Users).all()


@router.get("/auth/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK, tags=["Search Methods"])
async def get_users_by_id(db: db_dependency, user_id: int = Path(ge=1)):
    user_model = db.query(models.Users).filter(models.Users.id == user_id).first()

    if user_model is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_model


@router.delete("/auth/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Delete Methods"])
async def delete_users_by_id(db: db_dependency, user_id: int = Path(ge=1)):
    user_model = db.query(models.Users).filter(models.Users.id == user_id).first()

    if user_model is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user_model)
    db.commit()


@router.post("/auth", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Add Methods"])
async def add_users(db: db_dependency, user_request: UserCreate):
    new_user = models.Users(**user_request.model_dump())

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user
    except IntegrityError:
        db.rollback()

        raise HTTPException(status_code=409, detail="Duplicate values are not accepted")
    

@router.put("/auth/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK, tags=["Update Methods"])
async def update_users_by_id(db: db_dependency, user_request: UserCreate, user_id: int = Path(ge=1)):
    user_model = db.query(models.Users).filter(models.Users.id == user_id).first()

    if user_model is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        for field, value in user_request.model_dump().items():
            setattr(user_model, field, value)

        db.commit()
    except IntegrityError:
        db.rollback()
        
        raise HTTPException(status_code=409, detail="Duplicate values are not accepted")
    
    return user_model