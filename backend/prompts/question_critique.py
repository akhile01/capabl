from langchain_core.prompts import PromptTemplate

CRITIQUE_PROMPT = PromptTemplate.from_template(
    """ROLE
You are an expert educational reviewer and critic.

TASK
Evaluate the generated question based on the supplied context and quality criteria.

CONTEXT (Source Material)
{context}

GENERATED QUESTION TO EVALUATE
{question_json}

PRIOR QUESTIONS (Avoid Duplication)
{prior_questions}

CRITERIA
Evaluate the question based on the following:
1. Content Correctness: Is the answer correct according to the source?
2. Source Grounding: Can the answer be derived entirely from the retrieved context? Did it introduce external info?
3. Clarity: Is the wording clear and unambiguous?
4. Answer Uniqueness (MCQ): Is there exactly one defensibly correct option? No distractor should be arguably correct.
5. Distractor Quality (MCQ): Are distractors plausible, non-absurd, non-duplicate, and meaningfully incorrect?
6. Difficulty Calibration: Does the cognitive task match '{difficulty}'?
7. Bloom-level Alignment: Does the question test '{bloom_level}'?
8. Explanation: Does the explanation support the correct answer and is it consistent with the source?
9. Duplication: Does this question test essentially the same concept as any of the prior questions?

OUTPUT
Provide your evaluation strictly as a structured JSON object matching this schema:
{{
    "valid": boolean,
    "overall_score": float (0.0 to 1.0),
    "issues": [string] (List of specific issues if any),
    "correctness": {{"passed": boolean, "reason": string}},
    "grounding": {{"passed": boolean, "reason": string}},
    "clarity": {{"passed": boolean, "reason": string}},
    "answer_uniqueness": {{"passed": boolean, "reason": string}},
    "distractors": {{"passed": boolean, "reason": string}},
    "difficulty": {{"passed": boolean, "reason": string}}
}}

If the question fundamentally fails any criterion, set "valid" to false and provide a low "overall_score".
"""
)
