from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login or auto-register.
    If username exists, return the user.
    If not, create a new user.

    Note: P0 words (unlearned) are represented by absence of WordProgress records.
    """
    user_repo = UserRepository(db)
    user, is_new = user_repo.get_or_create(request.username)

    return LoginResponse(
        id=str(user.id),
        username=user.username,
        created_at=user.created_at,
        is_new_user=is_new,
    )
