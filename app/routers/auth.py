from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from app.repositories.user_repository import UserRepository
from app.utils.security import verify_password, get_password_hash, create_access_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Requires email, username, password
    - Email and username must be unique
    - Returns access token on successful registration
    """
    user_repo = UserRepository(db)

    # Check if email already exists
    if user_repo.email_exists(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    if user_repo.username_exists(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    hashed_password = get_password_hash(request.password)
    user = user_repo.create(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password
    )

    # Generate token
    access_token = create_access_token(user.id)

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        created_at=user.created_at,
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login.

    - Login with email + password
    - Returns access token (valid for 30 days)
    """
    user_repo = UserRepository(db)

    # Find user
    user = user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Generate token
    access_token = create_access_token(user.id)

    return LoginResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user info.

    - Requires Bearer Token authentication
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        current_level_id=current_user.current_level_id,
        current_category_id=current_user.current_category_id
    )
