from typing import Optional
from pydantic import BaseModel


class PerformanceLog(BaseModel):
    id: Optional[str] = None

    student_id: str

    question_id: str

    answer: str

    correct: bool

    attempt_number: int = 1

    hint_used: bool = False

    score: float = 0.0

    timestamp: Optional[str] = None