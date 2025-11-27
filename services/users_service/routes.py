# services/users_service/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib
import os

from . import models
from .schemas import UserCreate, UserLogin, UserResponse, Token
from .database import get_db

router = APIRouter(prefix="/users", tags=["users"])

# In this educational project we will use a very simple token scheme:
# - When the user logs in successfully, we return a "token" that is just
#   their username.
# - Other services can treat "access_token" as the authenticated username.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# Simple salted password hashing (for assignment/demo purposes)
PASSWORD_SALT = os.getenv("USER_PASSWORD_SALT", "change-me-in-production")


def hash_password(raw_password: str) -> str:
    """
    Hash a plaintext password using SHA-256 with a static salt.

    In a real production system, you would use a dedicated password
    hashing library (e.g., bcrypt/argon2) with per-user salts.
    """
    data = (PASSWORD_SALT + raw_password).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    """
    Check whether a user with the given username/password exists.

    Returns the User object if authentication succeeds, or None otherwise.
    """
    user = (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )
    if user is None:
        return None

    # Compare hashed password with stored value
    if user.password != hash_password(password):
        return None

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Retrieve the currently authenticated user from the access token.

    For this project, the token is simply the username; in a real system,
    this would be a signed JWT or similar.
    """
    username = token  # token is just the username in this simplified design
    user = (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Ensure that the current user has an admin-level role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    The password is hashed before storage for this assignment to avoid
    keeping plaintext credentials. In a production system you would use
    a stronger password hashing algorithm (e.g. bcrypt/argon2).
    """
    hashed_pw = hash_password(user.password)

    db_user = models.User(
        username=user.username,
        password=hashed_pw,
        role="regular",
    )
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(models.User)
            .filter(models.User.username == user.username)
            .first()
        )
        if existing:
            return existing
        raise HTTPException(status_code=400, detail="Username already exists")

    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a simple bearer token.

    The returned access_token is just the username, which is sufficient for
    demonstrating authentication and authorization in this project.
    """
    db_user = authenticate_user(db, user.username, user.password)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=db_user.username,
        token_type="bearer",
        role=db_user.role,
    )


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """
    List all registered users.

    For this assignment, this endpoint remains open so existing tests
    continue to work. Authentication and authorization are demonstrated
    on the reviews service.
    """
    users = db.query(models.User).all()
    return users
