from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

from app.schemas.common import ExerciseWithWordSchema


class LevelAnalysisExerciseSchema(ExerciseWithWordSchema):
    level_order: int


class LevelAnalysisSessionResponse(BaseModel):
    exercises: List[LevelAnalysisExerciseSchema]


class LevelAnalysisSubmitRequest(BaseModel):
    level_order: int


class LevelAnalysisSubmitResponse(BaseModel):
    success: bool
    current_level: Optional[Dict[str, Any]]
    current_category: Optional[Dict[str, Any]]
