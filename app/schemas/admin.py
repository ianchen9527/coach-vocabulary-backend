from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ResetProgressResponse(BaseModel):
    success: bool
    words_reset: int


class ResetCooldownResponse(BaseModel):
    success: bool
    words_affected: int


class WordInput(BaseModel):
    word: str
    translation: str
    sentence: Optional[str] = None
    sentence_zh: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    level_id: Optional[int] = None
    category_id: Optional[int] = None


class SeedWordsRequest(BaseModel):
    words: List[WordInput]
    clear_existing: bool = False


class SeedWordsResponse(BaseModel):
    success: bool
    words_imported: int
    words_skipped: int


class WordOutput(BaseModel):
    id: str
    word: str
    translation: str
    sentence: Optional[str] = None
    sentence_zh: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    level_id: Optional[int] = None
    category_id: Optional[int] = None
    created_at: datetime


class WordsListResponse(BaseModel):
    words: List[WordOutput]
    total_count: int
