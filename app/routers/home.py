from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.home import StatsResponse, WordPoolResponse, WordPoolItem
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get home page statistics."""
    progress_repo = ProgressRepository(db)
    user_id = current_user.id

    today_learned = progress_repo.count_today_learned(user_id)
    # Include both P pool practice and R pool practice phase
    available_practice = (
        progress_repo.count_available_practice(user_id) +
        progress_repo.count_r_pool_practice(user_id)
    )
    available_review = progress_repo.count_available_review(user_id)
    upcoming_24h = progress_repo.count_upcoming_24h(user_id)

    can_learn, _ = progress_repo.can_learn(user_id)
    can_practice, _ = progress_repo.can_practice(user_id)
    can_review, _ = progress_repo.can_review(user_id)

    next_available_time = None
    if not can_learn and not can_practice and not can_review:
        next_available_time = progress_repo.get_next_available_time(user_id)

    return StatsResponse(
        today_learned=today_learned,
        available_practice=available_practice,
        available_review=available_review,
        upcoming_24h=upcoming_24h,
        can_learn=can_learn,
        can_practice=can_practice,
        can_review=can_review,
        next_available_time=next_available_time,
        current_level={
            "id": current_user.current_level.id,
            "order": current_user.current_level.order,
            "label": current_user.current_level.label,
        } if current_user.current_level else None,
        current_category={
            "id": current_user.current_category.id,
            "order": current_user.current_category.order,
            "label": current_user.current_category.label,
        } if current_user.current_category else None,
    )


@router.get("/word-pool", response_model=WordPoolResponse)
def get_word_pool(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all words grouped by pool (for debugging)."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)

    pools = progress_repo.get_pool_summary(current_user.id)
    total_count = word_repo.count()

    # Convert to response format
    formatted_pools = {}
    for pool_name, items in pools.items():
        formatted_pools[pool_name] = [
            WordPoolItem(**item) for item in items
        ]

    return WordPoolResponse(
        pools=formatted_pools,
        total_count=total_count,
    )
