import pytest
import datetime
from unittest.mock import patch, MagicMock

from backend.agents.orchestrator import OrchestratorAgent
from database.tables import init_db
from database.connections import get_db_connection

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    # Clean up before each test
    conn = get_db_connection()
    conn.execute("DELETE FROM performance_logs")
    conn.execute("DELETE FROM spaced_repetition")
    conn.execute("DELETE FROM topic_mastery")
    conn.execute("DELETE FROM generated_questions")
    conn.execute("DELETE FROM students")
    conn.commit()
    conn.close()

@patch("backend.agents.orchestrator.QuestionGenerationAgent.generate_questions")
@patch("backend.agents.orchestrator.SocraticEvaluationAgent.evaluate")
def test_end_to_end_orchestrator(mock_eval, mock_gen):
    orchestrator = OrchestratorAgent()
    student_id = orchestrator.create_student("Test User")
    
    # 1. Initial State (No mastery, should pick a default or randomly retrieved topic)
    q_mock = MagicMock()
    q_mock.dict.return_value = {
        "question_text": "Q1",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "A",
        "explanation": "Exp1",
        "question_type": "mcq"
    }
    q_mock.id = "q1"
    q_mock.subject = "Unknown"
    mock_gen.return_value = {"questions": [q_mock]}
    
    next_q = orchestrator.get_next_question(student_id)
    assert next_q["status"] == "success"
    q_id = next_q["question"]["id"]
    topic = next_q["question"].get("topic", "Database systems")
    
    # 2. Answer Incorrectly -> Socratic Hint
    mock_eval.return_value = {
        "is_correct": False,
        "status": "retry",
        "feedback": "Hint 1"
    }
    
    res = orchestrator.process_answer(student_id, q_id, "B", attempt_count=1)
    assert res["status"] == "retry"
    assert res["is_correct"] is False
    assert "Hint 1" in res["feedback"]
    
    # Verify mastery is not yet updated because it's a retry state
    conn = get_db_connection()
    mastery = conn.execute("SELECT mastery_level FROM topic_mastery WHERE student_id = ?", (student_id,)).fetchone()
    assert mastery is None  # Not completed yet
    
    # 3. Answer Correctly on retry
    mock_eval.return_value = {
        "is_correct": True,
        "status": "completed",
        "feedback": "Good job."
    }
    res2 = orchestrator.process_answer(student_id, q_id, "A", attempt_count=2)
    assert res2["status"] == "completed"
    assert res2["is_correct"] is True
    
    # Verify mastery increased
    mastery = conn.execute("SELECT mastery_level FROM topic_mastery WHERE student_id = ?", (student_id,)).fetchone()
    assert mastery is not None
    assert mastery["mastery_level"] > 0.0
    
    # Verify performance logged
    logs = conn.execute("SELECT * FROM performance_logs WHERE student_id = ?", (student_id,)).fetchall()
    assert len(logs) == 2 # 2 attempts
    
    # Verify SR updated
    sr = conn.execute("SELECT * FROM spaced_repetition WHERE student_id = ?", (student_id,)).fetchone()
    assert sr is not None
    assert sr["interval"] == 1.0 # First successful review
    
    # 4. Answer incorrectly and max attempts
    q_mock2 = MagicMock()
    q_mock2.dict.return_value = {
        "question_text": "Q2",
        "options": ["1", "2", "3", "4"],
        "correct_answer": "1",
        "explanation": "Exp2"
    }
    mock_gen.return_value = {"questions": [q_mock2]}
    next_q2 = orchestrator.get_next_question(student_id)
    q_id2 = next_q2["question"]["id"]
    
    mock_eval.return_value = {
        "is_correct": False,
        "status": "completed", # Failed max attempts
        "feedback": "Final explanation."
    }
    
    mastery_before = mastery["mastery_level"]
    orchestrator.process_answer(student_id, q_id2, "2", attempt_count=3)
    
    # Mastery should decrease
    mastery_after = conn.execute("SELECT mastery_level FROM topic_mastery WHERE student_id = ?", (student_id,)).fetchone()["mastery_level"]
    assert mastery_after < mastery_before
    
    # SR should drop interval
    sr_after = conn.execute("SELECT * FROM spaced_repetition WHERE student_id = ?", (student_id,)).fetchone()
    assert sr_after["interval"] == 1.0
    assert sr_after["repetition"] == 0

    conn.close()
