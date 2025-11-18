# services/users_service/routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models
from .schemas import UserCreate, UserResponse
from .database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(
        username=user.username,
        password=user.password,  # (in a real app you’d hash this)
        role="regular",
    )
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        # Duplicate username → rollback and return existing user instead of crashing
        db.rollback()
        existing = (
            db.query(models.User)
            .filter(models.User.username == user.username)
            .first()
        )
        if existing:
            return existing

        # Fallback: something else went wrong with the constraint
        raise HTTPException(status_code=400, detail="Username already exists")

    db.refresh(db_user)
    return db_user

@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users