from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.common import WordDetailSchema, ExerciseSchema, AnswerSchema


class LearnSessionResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    words: List[WordDetailSchema]
    exercises: List[ExerciseSchema]


class LearnCompleteRequest(BaseModel):
    word_ids: List[str]
    answers: List[AnswerSchema]


class LearnCompleteResponse(BaseModel):
    success: bool
    words_moved: int
    today_learned: int
    next_available_time: Optional[datetime] = None
