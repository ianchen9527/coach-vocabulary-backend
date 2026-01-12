from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


# ============== Register ==============
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=100, description="Password")


class RegisterResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    access_token: str
    token_type: str = "bearer"


# ============== Login ==============
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    id: str
    email: str
    username: str
    access_token: str
    token_type: str = "bearer"


# ============== Token ==============
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============== Current User ==============
class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    is_active: bool
    current_level_id: Optional[int] = None
    current_category_id: Optional[int] = None

    class Config:
        from_attributes = True
