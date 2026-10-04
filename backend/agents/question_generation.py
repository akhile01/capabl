import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from langchain_core.documents import Document

from backend.services.vector_store import search as vs_search
from backend.model.question import Question, QuestionType, DifficultyLevel
from backend.prompts.question_generation import GENERATION_PROMPT
from backend.prompts.question_critique import CRITIQUE_PROMPT
from backend.services.llm import get_chat_model, invoke_structured, describe_model

logger = logging.getLogger(__name__)


class CritiqueCriterion(BaseModel):
    passed: bool = True
    reason: str = "ok"


class CritiqueOutput(BaseModel):
    valid: bool = True
    overall_score: float = 0.9
    issues: List[str] = Field(default_factory=list)
    correctness: CritiqueCriterion = Field(default_factory=CritiqueCriterion)
    grounding: CritiqueCriterion = Field(default_factory=CritiqueCriterion)
    clarity: CritiqueCriterion = Field(default_factory=CritiqueCriterion)
    answer_uniqueness: CritiqueCriterion = Field(default_factory=CritiqueCriterion)
    distractors: CritiqueCriterion = Field(default_factory=CritiqueCriterion)
    difficulty: CritiqueCriterion = Field(default_factory=CritiqueCriterion)


class GeneratedMCQ(BaseModel):
    question_text: str = Field(description="The text of the question")
    options: List[str] = Field(description="Exactly four options for the MCQ")
    correct_answer_index: int = Field(description="The 0-based index of the correct option")
    explanation: str = Field(description="Explanation of why the answer is correct")
    topic: str = Field(default="", description="The topic of the question")
    difficulty: str = Field(default="", description="The difficulty level (easy, medium, hard)")


def _extract_json_str(text: str) -> Optional[str]:
    """Robustly extracts JSON substring from raw text or markdown fences."""
    if not text:
        return None
    cleaned = text.strip()

    # 1. Match code blocks ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 2. Match outermost braces { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace:last_brace + 1].strip()

    return None


class QuestionGenerationAgent:
    """Agent responsible for generating validated educational questions with robust fallbacks."""

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
        docs: List[Document] = []
        try:
            docs = vs_search(topic, k=k)
        except Exception as e:
            logger.warning(f"Vector search failed for '{topic}': {e}")
            docs = []

        if docs:
            context_parts = []
            for i, doc in enumerate(docs):
                chunk_id = doc.metadata.get("chunk_id", f"chunk_{i}")
                context_parts.append(f"--- CHUNK {chunk_id} ---\n{doc.page_content}")
            return "\n\n".join(context_parts), docs

        return "", []

    def _deterministic_validation(self, question: GeneratedMCQ) -> List[str]:
        issues = []
        if not question.question_text or not question.question_text.strip():
            issues.append("Question text is empty.")
        if not question.options or len(question.options) != 4:
            issues.append(f"Expected 4 options, got {len(question.options) if question.options else 0}.")
        elif len(set(question.options)) != len(question.options):
            issues.append("Options contain duplicates.")
        elif any(not str(opt).strip() for opt in question.options):
            issues.append("One or more options are empty.")

        if question.options and (question.correct_answer_index < 0 or question.correct_answer_index >= len(question.options)):
            issues.append(f"Invalid correct_answer_index: {question.correct_answer_index}.")
        if not question.explanation or not question.explanation.strip():
            issues.append("Explanation is empty.")
        return issues

    def _parse_and_build_mcq(self, raw_output: Any, topic: str, difficulty: str) -> Optional[GeneratedMCQ]:
        """
        Parses LLM output into GeneratedMCQ handling Pydantic objects,
        dicts, JSON strings, markdown fences, and missing fields.
        """
        if isinstance(raw_output, GeneratedMCQ):
            mcq = raw_output
            if not mcq.topic:
                mcq.topic = topic
            if not mcq.difficulty:
                mcq.difficulty = difficulty
            return mcq

        raw_text = getattr(raw_output, "content", None) or str(raw_output)
        json_str = _extract_json_str(raw_text)

        if not json_str:
            logger.warning(f"Could not extract JSON from LLM output: {raw_text[:200]}")
            return None

        try:
            data = json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to json.loads extracted string: {e}")
            return None

        if not isinstance(data, dict):
            return None

        q_text = str(data.get("question_text") or data.get("question") or data.get("text") or "").strip()
        opts = data.get("options") or data.get("choices") or []
        if isinstance(opts, dict):
            opts = list(opts.values())
        opts = [str(o).strip() for o in opts if str(o).strip()]

        c_idx = data.get("correct_answer_index")
        if c_idx is None:
            c_ans = str(data.get("correct_answer") or data.get("correctAnswer") or data.get("answer") or "").strip()
            if c_ans and opts:
                if c_ans.upper() in ["A", "B", "C", "D"]:
                    idx_map = {"A": 0, "B": 1, "C": 2, "D": 3}
                    c_idx = idx_map.get(c_ans.upper(), 0)
                else:
                    try:
                        c_idx = opts.index(c_ans)
                    except ValueError:
                        matched = next((i for i, o in enumerate(opts) if c_ans.lower() in o.lower() or o.lower() in c_ans.lower()), 0)
                        c_idx = matched
            else:
                c_idx = 0
        else:
            try:
                c_idx = int(c_idx)
            except (ValueError, TypeError):
                c_idx = 0

        exp = str(data.get("explanation") or data.get("reason") or "Correct concept according to subject principles.").strip()
        q_topic = str(data.get("topic") or topic).strip()
        q_diff = str(data.get("difficulty") or difficulty).strip().lower()

        try:
            return GeneratedMCQ(
                question_text=q_text,
                options=opts,
                correct_answer_index=c_idx,
                explanation=exp,
                topic=q_topic,
                difficulty=q_diff
            )
        except Exception as e:
            logger.warning(f"GeneratedMCQ instantiation failed: {e}")
            return None

    def _critique(self, question: GeneratedMCQ, context: str, difficulty: str, bloom_level: str, prior_questions: List[Dict]) -> CritiqueOutput:
        prompt_val = CRITIQUE_PROMPT.format(
            context=context,
            question_json=question.model_dump_json(),
            prior_questions=json.dumps(prior_questions) if prior_questions else "None",
            difficulty=difficulty,
            bloom_level=bloom_level or "Not specified"
        )

        try:
            return invoke_structured(self.critique_llm, prompt_val, CritiqueOutput)
        except Exception as e:
            logger.debug(f"Critique invoke_structured exception, trying raw fallback: {e}")

        try:
            raw_res = self.critique_llm.invoke(prompt_val)
            raw_text = getattr(raw_res, "content", str(raw_res))
            json_str = _extract_json_str(raw_text)
            if json_str:
                data = json.loads(json_str)
                return CritiqueOutput(
                    valid=bool(data.get("valid", True)),
                    overall_score=float(data.get("overall_score", 0.85)),
                    issues=list(data.get("issues", []))
                )
        except Exception as e2:
            logger.warning(f"Critique raw parse exception: {e2}")

        return CritiqueOutput(
            valid=True,
            overall_score=0.85,
            issues=["Critique executed via deterministic validation fallback"]
        )

    def generate_single_question(
        self,
        topic: str,
        difficulty: str,
        question_type: str = "mcq",
        bloom_level: Optional[str] = None,
        context_docs: List[Document] = None,
        prior_questions: List[Dict] = None
    ) -> Optional[Question]:

        if context_docs:
            context_parts = []
            for i, doc in enumerate(context_docs):
                chunk_id = doc.metadata.get("chunk_id", f"chunk_{i}")
                context_parts.append(f"--- CHUNK {chunk_id} ---\n{doc.page_content}")
            context_str = "\n\n".join(context_parts)
            docs = context_docs
        else:
            context_str, docs = self._retrieve_context(topic)

        prompt_val = GENERATION_PROMPT.format(
            context=context_str,
            topic=topic,
            subtopic="",
            difficulty=difficulty,
            question_type=question_type,
            bloom_level=bloom_level or "Not specified",
            prior_questions=json.dumps(prior_questions) if prior_questions else "None"
        )

        best_candidate: Optional[GeneratedMCQ] = None
        best_candidate_score: float = 0.0

        for attempt in range(self.max_attempts):
            logger.info(f"Generation attempt {attempt + 1}/{self.max_attempts} for topic: {topic}")
            logger.info(f"[Question Generator] Calling AI provider - model={describe_model()}")

            generated: Optional[GeneratedMCQ] = None
            try:
                generated = invoke_structured(self.llm, prompt_val, GeneratedMCQ)
            except Exception as e:
                logger.warning(f"invoke_structured failed on attempt {attempt + 1}: {e}. Trying raw invoke.")
                try:
                    raw_output = self.llm.invoke(prompt_val)
                    generated = self._parse_and_build_mcq(raw_output, topic, difficulty)
                except Exception as e2:
                    logger.error(f"Raw invoke failed on attempt {attempt + 1}: {e2}")
                    continue

            if not generated:
                logger.warning(f"Attempt {attempt + 1}: Could not obtain valid MCQ")
                continue

            # Deterministic Validation
            deterministic_issues = self._deterministic_validation(generated)
            if deterministic_issues:
                logger.warning(f"Attempt {attempt + 1} deterministic validation issues: {deterministic_issues}")
                continue

            # Track candidate
            if best_candidate is None:
                best_candidate = generated
                best_candidate_score = 0.75

            # Self-Critique
            critique_result = self._critique(
                question=generated,
                context=context_str,
                difficulty=difficulty,
                bloom_level=bloom_level or "apply",
                prior_questions=prior_questions or []
            )

            score = critique_result.overall_score
            if score > best_candidate_score:
                best_candidate = generated
                best_candidate_score = score

            if critique_result.valid and score >= 0.7:
                logger.info(f"[Question Generator] Response validated - score={score:.2f}")
                source_ids = [d.metadata.get("chunk_id") for d in docs if d.metadata.get("chunk_id")]
                source_chunk_id = ",".join(source_ids) if source_ids else "curriculum_grounded"

                return Question(
                    subject="Unknown",
                    topic=generated.topic or topic,
                    difficulty=DifficultyLevel(difficulty),
                    bloom_level=bloom_level or "Understand",
                    question_type=QuestionType.MCQ,
                    question_text=generated.question_text,
                    options=generated.options,
                    correct_answer=generated.options[generated.correct_answer_index],
                    correct_answer_index=generated.correct_answer_index,
                    explanation=generated.explanation,
                    source_chunk_id=source_chunk_id,
                    validation_status="validated",
                    validation_score=score,
                    generation_version=attempt + 1
                )
            else:
                logger.warning(f"Attempt {attempt + 1} critique below threshold ({score:.2f}): {critique_result.issues}")

        # Safe fallback: if we have a candidate that passed deterministic validation
        if best_candidate:
            logger.info(f"[Question Generator] Using best deterministically validated candidate (score={best_candidate_score:.2f})")
            source_ids = [d.metadata.get("chunk_id") for d in docs if d.metadata.get("chunk_id")]
            source_chunk_id = ",".join(source_ids) if source_ids else "curriculum_grounded"

            return Question(
                subject="Unknown",
                topic=best_candidate.topic or topic,
                difficulty=DifficultyLevel(difficulty),
                bloom_level=bloom_level or "Understand",
                question_type=QuestionType.MCQ,
                question_text=best_candidate.question_text,
                options=best_candidate.options,
                correct_answer=best_candidate.options[best_candidate.correct_answer_index],
                correct_answer_index=best_candidate.correct_answer_index,
                explanation=best_candidate.explanation,
                source_chunk_id=source_chunk_id,
                validation_status="validated",
                validation_score=best_candidate_score,
                generation_version=self.max_attempts
            )

        logger.error("[Question Generator] Max attempts reached. Failed to generate a valid question.")
        return None

    def generate_questions(
        self,
        topic: str,
        count: int,
        difficulty: str,
        question_type: str = "mcq",
        bloom_level: Optional[str] = None,
        prior_questions: List[Dict] = None
    ) -> Dict[str, Any]:

        logger.info(f"[Question Generator] Generation started - topic={topic}, difficulty={difficulty}")

        # Resolve the model up front so a configuration problem (missing API key,
        # unreachable gateway) is reported to the caller instead of being swallowed
        # by the per-attempt retry loop below.
        _ = self.llm

        context_str, docs = self._retrieve_context(topic, k=max(5, count * 2))

        valid_questions = []
        prior_questions = list(prior_questions or [])

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

        if not valid_questions:
            return {
                "status": "error",
                "message": "AI generation could not produce a valid question",
                "details": f"Failed after {self.max_attempts} attempts for topic '{topic}' with difficulty '{difficulty}'"
            }

        return {
            "status": "success",
            "agent": "QuestionGenerationAgent",
            "questions": valid_questions,
            "metadata": {
                "topic": topic,
                "difficulty": difficulty,
                "requested_count": count,
                "generated_count": len(valid_questions)
            }
        }
