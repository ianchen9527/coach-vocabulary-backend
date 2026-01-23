from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.common import ExerciseWithWordSchema, AnswerSchema, AnswerResultSchema


class PracticeSessionResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    exercises: List[ExerciseWithWordSchema]
    exercise_order: List[str]


class PracticeSubmitRequest(BaseModel):
    answers: List[AnswerSchema]


class PracticeSummary(BaseModel):
    correct_count: int
    incorrect_count: int


class PracticeSubmitResponse(BaseModel):
    success: bool
    results: List[AnswerResultSchema]
    summary: PracticeSummary
    next_available_time: Optional[datetime] = None
