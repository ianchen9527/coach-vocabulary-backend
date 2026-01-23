from typing import List

from pydantic import BaseModel

from app.schemas.common import ExerciseSchema, WordDetailSchema


class TutorialStepSchema(ExerciseSchema):
    step: int


class VocabularyTutorialResponse(BaseModel):
    word: WordDetailSchema
    steps: List[TutorialStepSchema]


class TutorialCompleteResponse(BaseModel):
    success: bool
