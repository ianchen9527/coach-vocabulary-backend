from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_user_id
from app.schemas.learn import (
    LearnSessionResponse,
    LearnCompleteRequest,
    LearnCompleteResponse,
)
from app.schemas.common import WordDetailSchema, ExerciseSchema, OptionSchema
from app.repositories.progress_repository import ProgressRepository
from app.repositories.word_repository import WordRepository
from app.repositories.user_repository import UserRepository
from app.models.word_level import WordLevel
from app.models.word_category import WordCategory
from app.services.session_service import build_learn_exercise, build_word_detail
from app.services.spaced_repetition import get_next_available_time
from app.utils.constants import LEARN_SESSION_SIZE

router = APIRouter(prefix="/api/learn", tags=["learn"])


@router.get("/session", response_model=LearnSessionResponse)
def get_learn_session(
    user_id: UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get a learning session with 5 new words."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)
    user_repo = UserRepository(db)

    # Check if can learn
    can_learn, reason = progress_repo.can_learn(user_id)
    if not can_learn:
        # Check if actually completed everything or just daily limit
        # can_learn returns "no_words_in_p0" if totally empty
        return LearnSessionResponse(
            available=False,
            reason=reason,
            words=[],
            exercises=[],
        )

    user = user_repo.get_by_id(user_id)
    current_level_id = user.current_level_id
    current_category_id = user.current_category_id

    if current_level_id is None or current_category_id is None:
        raise HTTPException(
            status_code=400,
            detail="Level analysis required"
        )

    # Strategy:
    # 1. Fetch from current (level, category)
    # 2. If valid but < SIZE, fetch from next category/level in loop until full
    
    session_words = []
    
    # Get all levels and categories ordered for traversal
    levels = db.query(WordLevel).order_by(WordLevel.order).all()
    categories = db.query(WordCategory).order_by(WordCategory.order).all()
    
    # Build lookup maps for fast access
    level_map = {l.id: l for l in levels}
    category_map = {c.id: c for c in categories}
    
    # Find current indices in the ordered lists
    curr_level_idx = -1
    for i, l in enumerate(levels):
        if l.id == current_level_id:
            curr_level_idx = i
            break
            
    curr_cat_idx = -1
    for i, c in enumerate(categories):
        if c.id == current_category_id:
            curr_cat_idx = i
            break

    # Start loop
    temp_level_idx = curr_level_idx
    temp_cat_idx = curr_cat_idx
    
    # Safety break: if we still have -1 (e.g. invalid IDs)
    if temp_level_idx == -1 or temp_cat_idx == -1:
         # Fallback if pointers invalid
         p0_words = progress_repo.get_p0_words(user_id, limit=LEARN_SESSION_SIZE)
         session_words = p0_words
    else: 
        while len(session_words) < LEARN_SESSION_SIZE:
             # Check bounds
             if temp_level_idx >= len(levels):
                 break # End of content
             
             target_level = levels[temp_level_idx]
             
             if temp_cat_idx >= len(categories):
                 # Move to next level, first category
                 temp_level_idx += 1
                 temp_cat_idx = 0
                 continue
                 
             target_cat = categories[temp_cat_idx]
             
             needed = LEARN_SESSION_SIZE - len(session_words)
             fetched = progress_repo.get_p0_words(
                 user_id, 
                 limit=needed, 
                 level_id=target_level.id, 
                 category_id=target_cat.id
             )
             
             # Filter out duplicates if any (though get_p0_words excludes learned, and we move linearly)
             # But we might double fetch if logic is wrong. Here we are fetching IDs we haven't seen.
             session_words.extend(fetched)
             
             # Move to next category for next iteration if needed
             temp_cat_idx += 1

    if not session_words:
        return LearnSessionResponse(
            available=False,
            reason="no_words_in_p0",
            words=[],
            exercises=[],
        )

    # Get all words for generating options (distractors)
    all_words = word_repo.get_all()

    # Build word details and exercises
    words = []
    exercises = []

    for word in session_words:
        words.append(WordDetailSchema(**build_word_detail(word)))

        # Build exercise
        exercise_data = build_learn_exercise(word, all_words, session_words)
        exercises.append(ExerciseSchema(
            word_id=exercise_data["word_id"],
            type=exercise_data["type"],
            options=[OptionSchema(**opt) for opt in exercise_data["options"]],
            correct_index=exercise_data["correct_index"],
        ))

    return LearnSessionResponse(
        available=True,
        reason=None,
        words=words,
        exercises=exercises,
    )


@router.post("/complete", response_model=LearnCompleteResponse)
def complete_learn(
    request: LearnCompleteRequest,
    user_id: UUID = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Complete learning session, move words from P0 to P1."""
    progress_repo = ProgressRepository(db)
    word_repo = WordRepository(db)

    now = datetime.now(timezone.utc)
    next_time = get_next_available_time("P1")
    words_moved = 0

    for word_id_str in request.word_ids:
        try:
            word_id = UUID(word_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid word_id: {word_id_str}")

        # Check if word exists
        word = word_repo.get_by_id(word_id)
        if not word:
            raise HTTPException(status_code=404, detail=f"Word not found: {word_id_str}")

        # Check if already has progress record (not in P0)
        existing_progress = progress_repo.get_by_user_and_word(user_id, word_id)
        if existing_progress:
            raise HTTPException(status_code=400, detail=f"Word {word_id_str} is not in P0 pool")

        # Create new progress record for P1
        progress_repo.create_progress(
            user_id=user_id,
            word_id=word_id,
            pool="P1",
            learned_at=now,
            last_practice_time=now,
            next_available_time=next_time,
        )
        words_moved += 1
        
    # Update User Level/Category Logic
    # 1. Get user
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    # 2. Get all completed words objects to check their levels
    completed_word_ids = [UUID(wid) for wid in request.word_ids]
    completed_words = word_repo.get_by_ids(completed_word_ids)
    
    # 3. Find max rank
    # Use 0 as default if level/category is missing
    max_level_order = -1
    max_cat_order = -1
    max_level_id = user.current_level_id
    max_cat_id = user.current_category_id
    
    # Helper to get order
    # (Optimized: we could join or pre-fetch, but for 5 words individual lazy loads or small queries are ok)
    # Actually word.level and word.category are relationships, let's assume they are joined or eager loaded?
    # word_repo.get_all() doesn't join by default but get_by_ids uses simple query.
    # Safe to access attributes, SQLAlchemy will lazy load.
    
    for w in completed_words:
        if not w.level or not w.category:
            continue
            
        w_l_order = w.level.order
        w_c_order = w.category.order
        
        # Compare tuple (level_order, cat_order)
        if (w_l_order > max_level_order) or \
           (w_l_order == max_level_order and w_c_order > max_cat_order):
            max_level_order = w_l_order
            max_cat_order = w_c_order
            max_level_id = w.level.id
            max_cat_id = w.category.id
            
    # 4. Compare with user current
    current_level = db.query(WordLevel).filter(WordLevel.id == user.current_level_id).first()
    current_cat = db.query(WordCategory).filter(WordCategory.id == user.current_category_id).first()
    
    curr_l_order = current_level.order if current_level else 0
    curr_c_order = current_cat.order if current_cat else 0
    
    if (max_level_order > curr_l_order) or \
       (max_level_order == curr_l_order and max_cat_order > curr_c_order):
        # Update user
        user.current_level_id = max_level_id
        user.current_category_id = max_cat_id
        db.commit()

    today_learned = progress_repo.count_today_learned(user_id)

    return LearnCompleteResponse(
        success=True,
        words_moved=words_moved,
        today_learned=today_learned,
    )
