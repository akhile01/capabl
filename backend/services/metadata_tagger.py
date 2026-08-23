import json
import os
import re
from typing import Any, Dict
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm() -> ChatGoogleGenerativeAI:
    """Initializes and returns the ChatGoogleGenerativeAI instance.

    Reads the API key from GEMINI_API_KEY, GOOGLE_API_KEY, or API_KEY env variables.

    Returns:
        ChatGoogleGenerativeAI instance.

    Raises:
        ValueError: If no API key is found in environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables."
        )

    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", google_api_key=api_key, temperature=0.0
    )


# Structured prompt designed to ensure LLM outputs parseable JSON
TAGGING_PROMPT = PromptTemplate.from_template(
    "Analyze the following text chunk and generate metadata. "
    "Provide your response strictly as a valid JSON object with keys 'topic', 'difficulty', and 'bloom_level'.\n"
    "Difficulty must be one of: 'easy', 'medium', 'hard'.\n"
    "Bloom's taxonomy level must be one of: 'remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'.\n"
    "Topic should be a concise label for the primary subject matter of the text.\n\n"
    "Chunk Text:\n{text}\n\n"
    "Response (JSON only):"
)


def tag_chunk(text: str) -> Dict[str, str]:
    """Generates structured topic, difficulty, and Bloom's level tagging for a text chunk.

    If tagging fails, returns safe fallback values.

    Args:
        text: The text content of the chunk to tag.

    Returns:
        A dictionary with keys 'topic', 'difficulty', and 'bloom_level'.
    """
    fallback = {
        "topic": "unknown",
        "difficulty": "unknown",
        "bloom_level": "unknown",
    }
    try:
        llm = get_llm()
        prompt_val = TAGGING_PROMPT.format(text=text)
        response = llm.invoke(prompt_val)

        content = response.content.strip()

        # Extract JSON from potential codeblock format (e.g. ```json ... ```)
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        data = json.loads(content)

        # Standardize difficulty and bloom_level values
        difficulty = str(data.get("difficulty", "unknown")).strip().lower()
        if difficulty not in ["easy", "medium", "hard"]:
            difficulty = "unknown"

        bloom_level = str(data.get("bloom_level", "unknown")).strip().lower()
        valid_blooms = [
            "remember",
            "understand",
            "apply",
            "analyze",
            "evaluate",
            "create",
        ]
        if bloom_level not in valid_blooms:
            bloom_level = "unknown"

        return {
            "topic": str(data.get("topic", "unknown")).strip(),
            "difficulty": difficulty,
            "bloom_level": bloom_level,
        }
    except Exception as e:
        # Graceful handling so failing to tag does not crash ingestion
        return fallback
