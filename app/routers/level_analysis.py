from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_user_id
from app.schemas.level_analysis import (
    LevelAnalysisSessionResponse,
    LevelAnalysisSubmitRequest,
    LevelAnalysisSubmitResponse,
    LevelAnalysisExerciseSchema,
)
from app.repositories.word_repository import WordRepository
from app.models.user import User
from app.models.word_level import WordLevel
from app.models.word_category import WordCategory
from app.services.session_service import generate_options
from app.utils.constants import ExerciseType

router = APIRouter(prefix="/api/level-analysis", tags=["level-analysis"])


@router.get("/session", response_model=LevelAnalysisSessionResponse)
def get_analysis_session(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Get random exercises from each level for analysis."""
    word_repo = WordRepository(db)
    
    # Get all levels ordered
    levels = db.query(WordLevel).order_by(WordLevel.order).all()
    
    # Get all words for generating options (distractors)
    all_words = word_repo.get_all()
    
    exercises: List[LevelAnalysisExerciseSchema] = []
    
    for level in levels:
        # Get 10 random words for this level
        words = word_repo.get_random_words_by_level(level.id, 10)
        
        for word in words:
            # Generate options
            options, correct_index = generate_options(word, all_words)
            
            exercises.append(LevelAnalysisExerciseSchema(
                word_id=str(word.id),
                word=word.word,
                translation=word.translation,
                image_url=word.image_url,
                audio_url=word.audio_url,
                pool="P0", # Conceptually these are new words
                type=ExerciseType.READING_LV1.value,
                options=options,
                correct_index=correct_index,
                level_order=level.order,
            ))
            
    return LevelAnalysisSessionResponse(exercises=exercises)


@router.post("/submit", response_model=LevelAnalysisSubmitResponse)
def submit_analysis(
    request: LevelAnalysisSubmitRequest,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db)
):
    """Submit level analysis result and update user level."""
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get level by order
    level = db.query(WordLevel).filter(WordLevel.order == request.level_order).first()
    if not level:
        raise HTTPException(status_code=404, detail=f"Level order {request.level_order} not found")
        
    # Get category with order 1 (default)
    category = db.query(WordCategory).filter(WordCategory.order == 1).first()
    if not category:
        raise HTTPException(status_code=500, detail="Default category (order 1) not found")
        
    # Update user
    user.current_level_id = level.id
    user.current_category_id = category.id
    db.commit()
    db.refresh(user)
    
    return LevelAnalysisSubmitResponse(
        success=True,
        current_level={
            "id": user.current_level.id,
            "order": user.current_level.order,
            "label": user.current_level.label,
        } if user.current_level else None,
        current_category={
            "id": user.current_category.id,
            "order": user.current_category.order,
            "label": user.current_category.label,
        } if user.current_category else None,
    )
