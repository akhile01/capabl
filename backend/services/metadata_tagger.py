import json
import os
import re
from typing import Dict

try:
    from langchain_core.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    PromptTemplate = None
    class ChatGoogleGenerativeAI:
        pass


def get_llm():
    """Initializes and returns the chat model instance for tagging."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=api_key,
                temperature=0.0,
            )
        except Exception:
            pass

    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    if provider in ("clean", "nova", "openai") or os.getenv("CLEAN_API_KEY"):
        try:
            from backend.services.llm import get_chat_model
            return get_chat_model(temperature=0.0)
        except Exception:
            pass
    return None


TAGGING_PROMPT_TEMPLATE = (
    "Analyze the following text chunk and generate metadata. "
    "Provide your response strictly as a valid JSON object with keys 'topic', 'difficulty', and 'bloom_level'.\n"
    "Difficulty must be one of: 'easy', 'medium', 'hard'.\n"
    "Bloom's taxonomy level must be one of: 'remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'.\n"
    "Topic should be a concise label for the primary subject matter of the text.\n\n"
    "Chunk Text:\n{text}\n\n"
    "Response (JSON only):"
)


def tag_chunk(text: str) -> Dict[str, str]:
    """Generates structured topic, difficulty, and Bloom's level tagging for a text chunk."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    fallback_topic = lines[0] if lines else "unknown"
    fallback = {
        "topic": fallback_topic,
        "difficulty": "unknown",
        "bloom_level": "unknown",
    }

    llm = get_llm()
    if not llm:
        return fallback

    try:
        if PromptTemplate:
            prompt_val = PromptTemplate.from_template(TAGGING_PROMPT_TEMPLATE).format(text=text)
        else:
            prompt_val = TAGGING_PROMPT_TEMPLATE.replace("{text}", text)

        response = llm.invoke(prompt_val)
        content = getattr(response, "content", str(response)).strip()

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        data = json.loads(content)

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
            "topic": str(data.get("topic", fallback_topic)).strip(),
            "difficulty": difficulty,
            "bloom_level": bloom_level,
        }
    except Exception:
        return fallback

