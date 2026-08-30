import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from backend.agents.question_generation import (
    QuestionGenerationAgent,
    GeneratedMCQ,
    CritiqueOutput,
    CritiqueCriterion
)
from backend.model.question import Question, DifficultyLevel

@pytest.fixture
def agent():
    with patch("backend.agents.question_generation.ChatGoogleGenerativeAI"):
        yield QuestionGenerationAgent()

def test_deterministic_validation_valid(agent):
    mcq = GeneratedMCQ(
        question_text="What is ACID?",
        options=["A", "B", "C", "D"],
        correct_answer_index=1,
        explanation="Because.",
        topic="DBMS",
        difficulty="medium"
    )
    issues = agent._deterministic_validation(mcq)
    assert not issues

def test_deterministic_validation_invalid_options(agent):
    mcq = GeneratedMCQ(
        question_text="What is ACID?",
        options=["A", "A", "C", "D"], # duplicate
        correct_answer_index=5, # invalid index
        explanation="", # empty
        topic="DBMS",
        difficulty="medium"
    )
    issues = agent._deterministic_validation(mcq)
    assert len(issues) == 3
    assert "Options contain duplicates." in issues
    assert "Invalid correct_answer_index: 5." in issues
    assert "Explanation is empty." in issues
    
@patch("backend.agents.question_generation.vs_search")
def test_retrieve_context_empty(mock_search, agent):
    mock_search.return_value = []
    text, docs = agent._retrieve_context("Test")
    assert text == ""
    assert len(docs) == 0

@patch.object(QuestionGenerationAgent, '_critique')
@patch.object(QuestionGenerationAgent, '_retrieve_context')
def test_generate_single_question_success(mock_retrieve, mock_critique, agent):
    doc = Document(page_content="ACID means Atomicity, Consistency, Isolation, Durability.", metadata={"chunk_id": "123"})
    mock_retrieve.return_value = ("--- CHUNK 123 ---\nACID...", [doc])
    
    mock_critique.return_value = CritiqueOutput(
        valid=True,
        overall_score=1.0,
        issues=[],
        correctness=CritiqueCriterion(passed=True, reason=""),
        grounding=CritiqueCriterion(passed=True, reason=""),
        clarity=CritiqueCriterion(passed=True, reason=""),
        answer_uniqueness=CritiqueCriterion(passed=True, reason=""),
        distractors=CritiqueCriterion(passed=True, reason=""),
        difficulty=CritiqueCriterion(passed=True, reason="")
    )
    
    mcq = GeneratedMCQ(
        question_text="What does the A in ACID stand for?",
        options=["Atomicity", "Accuracy", "Action", "Axiom"],
        correct_answer_index=0,
        explanation="A stands for Atomicity.",
        topic="Transactions",
        difficulty="medium"
    )
    
    # Mock LLM generation
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mcq
    agent.llm.with_structured_output.return_value = mock_llm
    
    q = agent.generate_single_question("Transactions", "medium")
    
    assert isinstance(q, Question)
    assert q.question_text == "What does the A in ACID stand for?"
    assert q.correct_answer == "Atomicity"
    assert q.correct_answer_index == 0
    assert q.source_chunk_id == "123"
    assert q.validation_status == "validated"

@patch.object(QuestionGenerationAgent, '_critique')
def test_generate_single_question_retry(mock_critique, agent):
    # First critique fails, second succeeds
    doc = Document(page_content="ACID", metadata={"chunk_id": "1"})
    
    fail_critique = CritiqueOutput(
        valid=False, overall_score=0.4, issues=["Ambiguous"],
        correctness=CritiqueCriterion(passed=False, reason=""),
        grounding=CritiqueCriterion(passed=True, reason=""),
        clarity=CritiqueCriterion(passed=False, reason=""),
        answer_uniqueness=CritiqueCriterion(passed=True, reason=""),
        distractors=CritiqueCriterion(passed=True, reason=""),
        difficulty=CritiqueCriterion(passed=True, reason="")
    )
    pass_critique = CritiqueOutput(
        valid=True, overall_score=0.9, issues=[],
        correctness=CritiqueCriterion(passed=True, reason=""),
        grounding=CritiqueCriterion(passed=True, reason=""),
        clarity=CritiqueCriterion(passed=True, reason=""),
        answer_uniqueness=CritiqueCriterion(passed=True, reason=""),
        distractors=CritiqueCriterion(passed=True, reason=""),
        difficulty=CritiqueCriterion(passed=True, reason="")
    )
    mock_critique.side_effect = [fail_critique, pass_critique]
    
    mcq = GeneratedMCQ(
        question_text="Test?", options=["1","2","3","4"], correct_answer_index=0,
        explanation="Exp", topic="Test", difficulty="easy"
    )
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mcq
    agent.llm.with_structured_output.return_value = mock_llm
    
    q = agent.generate_single_question("Test", "easy", context_docs=[doc])
    
    assert q is not None
    assert q.generation_version == 2

@patch.object(QuestionGenerationAgent, 'generate_single_question')
@patch.object(QuestionGenerationAgent, '_retrieve_context')
def test_generate_multiple_questions(mock_retrieve, mock_generate_single, agent):
    doc = Document(page_content="ACID", metadata={"chunk_id": "1"})
    mock_retrieve.return_value = ("Context", [doc])
    
    q = Question(subject="S", topic="T", difficulty=DifficultyLevel.EASY, question_text="Q", correct_answer="A")
    mock_generate_single.return_value = q
    
    result = agent.generate_questions("Test", 2, "easy")
    
    assert result["agent"] == "QuestionGenerationAgent"
    assert len(result["questions"]) == 2
    assert result["metadata"]["requested_count"] == 2
    assert result["metadata"]["generated_count"] == 2
