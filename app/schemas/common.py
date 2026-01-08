from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class OptionSchema(BaseModel):
    index: int
    word_id: str
    translation: str
    image_url: Optional[str] = None


class ExerciseSchema(BaseModel):
    word_id: str
    type: str
    options: List[OptionSchema]
    correct_index: Optional[int] = None


class ExerciseWithWordSchema(ExerciseSchema):
    word: str
    translation: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    pool: str


class WordDetailSchema(BaseModel):
    id: str
    word: str
    translation: str
    sentence: Optional[str] = None
    sentence_zh: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None


class WordDetailWithPoolSchema(WordDetailSchema):
    pool: str


class AnswerSchema(BaseModel):
    word_id: str
    correct: bool


class AnswerResultSchema(BaseModel):
    word_id: str
    correct: bool
    previous_pool: str
    new_pool: str
    next_available_time: datetime
