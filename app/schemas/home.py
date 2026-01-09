from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel


class StatsResponse(BaseModel):
    today_learned: int
    available_practice: int
    available_review: int
    upcoming_24h: int
    can_learn: bool
    can_practice: bool
    can_review: bool
    next_available_time: Optional[datetime] = None
    current_level: Optional[Dict[str, Any]] = None
    current_category: Optional[Dict[str, Any]] = None


class WordPoolItem(BaseModel):
    word_id: str
    word: str
    translation: str
    next_available_time: Optional[str] = None


class WordPoolResponse(BaseModel):
    pools: Dict[str, List[WordPoolItem]]
    total_count: int
