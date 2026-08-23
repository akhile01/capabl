from typing import Dict, Optional
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    id: Optional[str] = None

    name: str

    subject: Optional[str] = None

    topic_mastery: Dict[str, float] = Field(default_factory=dict)

    questions_attempted: int = 0

    questions_correct: int = 0

    last_activity: Optional[str] = None
