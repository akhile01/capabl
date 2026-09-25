import json
import os
import re
from typing import Dict

# Simple fallback tagging – returns unknown for everything.
# In a real system this would call an LLM, but for local dev we avoid heavy deps.

def get_llm():
    """Placeholder for LLM initialization – returns None.
    """
    return None

# Simple deterministic stub: attempt to extract a topic from the first line
# and set difficulty/bloom_level to 'unknown'.
def tag_chunk(text: str) -> Dict[str, str]:
    """Generate basic metadata for a text chunk without external services.

    Returns a dict with keys 'topic', 'difficulty', 'bloom_level'.
    """
    # Very naive extraction: first non-empty line as topic
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    topic = lines[0] if lines else "unknown"
    return {
        "topic": topic,
        "difficulty": "unknown",
        "bloom_level": "unknown",
    }
