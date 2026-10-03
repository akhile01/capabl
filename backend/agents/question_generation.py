import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from langchain_core.documents import Document

from backend.services.vector_store import search as vs_search
from backend.model.question import Question, QuestionType, DifficultyLevel
from backend.prompts.question_generation import GENERATION_PROMPT
from backend.prompts.question_critique import CRITIQUE_PROMPT
from backend.services.llm import get_chat_model, invoke_structured

logger = logging.getLogger(__name__)

class CritiqueCriterion(BaseModel):
    passed: bool
    reason: str

class CritiqueOutput(BaseModel):
    valid: bool
    overall_score: float
    issues: List[str]
    correctness: CritiqueCriterion
    grounding: CritiqueCriterion
    clarity: CritiqueCriterion
    answer_uniqueness: CritiqueCriterion
    distractors: CritiqueCriterion
    difficulty: CritiqueCriterion


class GeneratedMCQ(BaseModel):
    question_text: str = Field(description="The text of the question")
    options: List[str] = Field(description="Exactly four options for the MCQ")
    correct_answer_index: int = Field(description="The 0-based index of the correct option")
    explanation: str = Field(description="Explanation of why the answer is correct")
    topic: str = Field(description="The topic of the question")
    difficulty: str = Field(description="The difficulty level (easy, medium, hard)")


class QuestionGenerationAgent:
    """Agent responsible for generating validated educational questions."""

    def __init__(self):
        # Models are created lazily so the server can start (and the UI can
        # report a clear error) even when no LLM credentials are configured yet.
        self._llm = None
        self._critique_llm = None
        self.max_attempts = int(os.getenv("MAX_GENERATION_ATTEMPTS", "3"))

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._get_llm(temperature=0.2)
        return self._llm

    @llm.setter
    def llm(self, value):
        self._llm = value

    @property
    def critique_llm(self):
        if self._critique_llm is None:
            self._critique_llm = self._get_llm(temperature=0.0)
        return self._critique_llm

    @critique_llm.setter
    def critique_llm(self, value):
        self._critique_llm = value
        
    def _get_llm(self, temperature: float = 0.2):
        # Provider (Nova API / Gemini) and model come from .env; see backend/services/llm.py
        return get_chat_model(temperature=temperature)

    def _retrieve_context(self, topic: str, k: int = 5) -> Tuple[str, List[Document]]:
        docs = vs_search(topic, k=k)
        if not docs:
            return "", []
        
        context_parts = []
        for i, doc in enumerate(docs):
            chunk_id = doc.metadata.get("chunk_id", f"chunk_{i}")
            context_parts.append(f"--- CHUNK {chunk_id} ---\n{doc.page_content}")
            
        return "\n\n".join(context_parts), docs
        
    def _deterministic_validation(self, question: GeneratedMCQ) -> List[str]:
        issues = []
        if not question.question_text.strip():
            issues.append("Question text is empty.")
        if len(question.options) != 4:
            issues.append(f"Expected 4 options, got {len(question.options)}.")
        if len(set(question.options)) != len(question.options):
            issues.append("Options contain duplicates.")
        if any(not opt.strip() for opt in question.options):
            issues.append("One or more options are empty.")
        if question.correct_answer_index < 0 or question.correct_answer_index >= len(question.options):
            issues.append(f"Invalid correct_answer_index: {question.correct_answer_index}.")
        if not question.explanation.strip():
            issues.append("Explanation is empty.")
        return issues
        
    def _critique(self, question: GeneratedMCQ, context: str, difficulty: str, bloom_level: str, prior_questions: List[Dict]) -> CritiqueOutput:
        try:
            prompt_val = CRITIQUE_PROMPT.format(
                context=context,
                question_json=question.model_dump_json(),
                prior_questions=json.dumps(prior_questions) if prior_questions else "None",
                difficulty=difficulty,
                bloom_level=bloom_level or "Not specified"
            )
            return invoke_structured(self.critique_llm, prompt_val, CritiqueOutput)
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            return CritiqueOutput(
                valid=False, overall_score=0.0, issues=[f"Critique execution failed: {str(e)}"],
                correctness=CritiqueCriterion(passed=False, reason="error"),
                grounding=CritiqueCriterion(passed=False, reason="error"),
                clarity=CritiqueCriterion(passed=False, reason="error"),
                answer_uniqueness=CritiqueCriterion(passed=False, reason="error"),
                distractors=CritiqueCriterion(passed=False, reason="error"),
                difficulty=CritiqueCriterion(passed=False, reason="error")
            )
            
    def generate_single_question(self, topic: str, difficulty: str, question_type: str = "mcq", bloom_level: Optional[str] = None, context_docs: List[Document] = None, prior_questions: List[Dict] = None) -> Optional[Question]:
        
        if context_docs:
            context_parts = []
            for i, doc in enumerate(context_docs):
                chunk_id = doc.metadata.get("chunk_id", f"chunk_{i}")
                context_parts.append(f"--- CHUNK {chunk_id} ---\n{doc.page_content}")
            context_str = "\n\n".join(context_parts)
            docs = context_docs
        else:
            context_str, docs = self._retrieve_context(topic)
            
        if not context_str.strip():
            logger.error("No context available for generation.")
            return None
            
        for attempt in range(self.max_attempts):
            logger.info(f"Generation attempt {attempt + 1}/{self.max_attempts} for topic: {topic}")
            
            prompt_val = GENERATION_PROMPT.format(
                context=context_str,
                topic=topic,
                subtopic="",
                difficulty=difficulty,
                question_type=question_type,
                bloom_level=bloom_level or "Not specified",
                prior_questions=json.dumps(prior_questions) if prior_questions else "None"
            )
            
            try:
                # 1. LLM Generation
                generated: GeneratedMCQ = invoke_structured(self.llm, prompt_val, GeneratedMCQ)
                
                # 2. Deterministic Validation
                deterministic_issues = self._deterministic_validation(generated)
                if deterministic_issues:
                    logger.warning(f"Deterministic validation failed: {deterministic_issues}")
                    continue
                    
                # 3. Self-Critique
                critique_result: CritiqueOutput = self._critique(
                    question=generated,
                    context=context_str,
                    difficulty=difficulty,
                    bloom_level=bloom_level,
                    prior_questions=prior_questions
                )
                
                if critique_result.valid and critique_result.overall_score >= 0.8:
                    logger.info("Question passed validation and critique.")
                    
                    # Convert to final Question model
                    source_ids = [d.metadata.get("chunk_id") for d in docs if d.metadata.get("chunk_id")]
                    source_chunk_id = ",".join(source_ids) if source_ids else None
                    
                    return Question(
                        subject="Unknown", # To be filled by orchestrator
                        topic=generated.topic or topic,
                        difficulty=DifficultyLevel(difficulty),
                        bloom_level=bloom_level,
                        question_type=QuestionType.MCQ,
                        question_text=generated.question_text,
                        options=generated.options,
                        correct_answer=generated.options[generated.correct_answer_index],
                        correct_answer_index=generated.correct_answer_index,
                        explanation=generated.explanation,
                        source_chunk_id=source_chunk_id,
                        validation_status="validated",
                        validation_score=critique_result.overall_score,
                        generation_version=attempt + 1
                    )
                else:
                    logger.warning(f"Critique failed. Score: {critique_result.overall_score}. Issues: {critique_result.issues}")
            except Exception as e:
                logger.error(f"Generation exception: {e}")
                
        logger.error("Max attempts reached. Failed to generate a valid question.")
        return None
        
    def generate_questions(self, topic: str, count: int, difficulty: str, question_type: str = "mcq", bloom_level: Optional[str] = None, prior_questions: List[Dict] = None) -> Dict[str, Any]:
        
        context_str, docs = self._retrieve_context(topic, k=max(5, count * 2))
        if not docs:
            return {"status": "error", "message": "No context found"}

        # Resolve the model up front so a configuration problem (missing API key,
        # unreachable gateway) is reported to the caller instead of being swallowed
        # by the per-attempt retry loop below.
        _ = self.llm
            
        valid_questions = []
        prior_questions = prior_questions or []
        
        for _ in range(count):
            q = self.generate_single_question(
                topic=topic,
                difficulty=difficulty,
                question_type=question_type,
                bloom_level=bloom_level,
                context_docs=docs,
                prior_questions=prior_questions
            )
            if q:
                valid_questions.append(q)
                prior_questions.append({"question": q.question_text, "correct_answer": q.correct_answer})
                
        return {
            "agent": "QuestionGenerationAgent",
            "questions": valid_questions,
            "metadata": {
                "topic": topic,
                "difficulty": difficulty,
                "requested_count": count,
                "generated_count": len(valid_questions)
            }
        }
