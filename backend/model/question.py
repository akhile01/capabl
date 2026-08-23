from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    id: Optional[str] = None

    subject: str
    topic: str

    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM

    bloom_level: Optional[str] = None

    question_type: QuestionType = QuestionType.MCQ

    question_text: str

    options: Optional[List[str]] = None

    correct_answer: str

    explanation: Optional[str] = None

    source_chunk_id: Optional[str] = None
