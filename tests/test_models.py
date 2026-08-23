from backend.model import (
    Question,
    StudentProfile,
    PerformanceLog,
    QuestionType,
    DifficultyLevel,
)


def test_question():

    question = Question(
        id="q001",
        subject="DBMS",
        topic="Normalization",
        difficulty=DifficultyLevel.MEDIUM,
        bloom_level="Understand",
        question_type=QuestionType.MCQ,
        question_text="Which normal form removes partial dependency?",
        options=[
            "1NF",
            "2NF",
            "3NF",
            "BCNF"
        ],
        correct_answer="2NF",
        explanation="2NF removes partial dependency.",
        source_chunk_id="chunk_001"
    )

    print("\nQUESTION:")
    print(question.model_dump())


def test_student():

    student = StudentProfile(
        id="student_001",
        name="Test Student",
        subject="DBMS",
        topic_mastery={
            "Normalization": 0.45,
            "SQL": 0.80
        }
    )

    print("\nSTUDENT:")
    print(student.model_dump())


def test_performance():

    performance = PerformanceLog(
        id="perf_001",
        student_id="student_001",
        question_id="q001",
        answer="1NF",
        correct=False,
        attempt_number=1,
        hint_used=True,
        score=0.0
    )

    print("\nPERFORMANCE:")
    print(performance.model_dump())