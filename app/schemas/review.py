from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.common import (
    WordDetailWithPoolSchema,
    ExerciseSchema,
    AnswerSchema,
)


class ReviewSessionResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    words: List[WordDetailWithPoolSchema]
    exercises: List[ExerciseSchema]


class ReviewCompleteRequest(BaseModel):
    word_ids: List[str]
    answers: List[AnswerSchema]


class ReviewCompleteResponse(BaseModel):
    success: bool
    words_completed: int
    next_available_time: Optional[datetime] = None
