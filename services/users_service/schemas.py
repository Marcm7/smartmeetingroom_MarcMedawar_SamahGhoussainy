from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Common fields shared by all user-related schemas."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9_]+$",
        description="Unique username (3–30 chars, letters/digits/underscore).",
    )


class UserCreate(UserBase):
    """Payload used when registering a new user."""
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Plain-text password for this project (would be hashed in a real app).",
    )


class UserLogin(UserBase):
    """Payload used when authenticating an existing user."""
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Password that must match the stored user password.",
    )


class UserResponse(UserBase):
    """Representation of a user returned by the API."""
    id: int
    role: str = "regular"

    class Config:
        orm_mode = True


class Token(BaseModel):
    """
    Authentication token returned after a successful login.

    access_token: A simple bearer token (here we use the username as token).
    token_type: Usually 'bearer'.
    role: The role associated with the authenticated user.
    """
    access_token: str
    token_type: str = "bearer"
    role: str
