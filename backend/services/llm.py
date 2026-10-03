"""Chat-model factory shared by every agent.

Two providers are supported, selected by ``LLM_PROVIDER`` or auto-detected
from which API key is present:

* ``nova``   – any OpenAI-compatible gateway (Nova API). Configure
               ``NOVA_API_KEY``, ``NOVA_BASE_URL`` and optionally ``NOVA_MODEL``.
               When ``NOVA_MODEL`` is unset the gateway's model list is fetched
               once and the strongest model is chosen from ``NOVA_MODEL_PREFERENCES``.
* ``gemini`` – Google Gemini via ``GEMINI_API_KEY`` (the original setup).
"""
import json
import logging
import os
import re
from functools import lru_cache
from typing import Any, List, Optional, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_NOVA_BASE_URL = "https://api.novaapi.ai/v1"

# Ordered "best first". Matched case-insensitively as substrings of the model id.
DEFAULT_MODEL_PREFERENCES = [
    "claude-opus-4", "claude-opus", "gpt-5", "o3-pro", "o3",
    "claude-sonnet-4", "gemini-3", "gemini-2.5-pro", "gpt-4.1",
    "claude-sonnet", "deepseek-r1", "gpt-4o", "gemini-2.5-flash",
    "deepseek", "llama", "qwen", "mistral",
]

# Never auto-pick these: they are not chat models.
_NON_CHAT_HINTS = ("embed", "whisper", "tts", "dall-e", "image", "audio", "moderation",
                   "rerank", "vision-only", "sora", "video", "speech")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def get_provider() -> str:
    explicit = (_env("LLM_PROVIDER") or "").lower()
    if explicit in ("nova", "openai", "gemini", "google"):
        return "gemini" if explicit == "google" else ("nova" if explicit == "openai" else explicit)
    if _env("NOVA_API_KEY"):
        return "nova"
    if _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY"):
        return "gemini"
    raise ValueError(
        "No LLM credentials found. Set NOVA_API_KEY (plus NOVA_BASE_URL) for the Nova API, "
        "or GEMINI_API_KEY for Google Gemini, in your .env file."
    )


def model_preferences() -> List[str]:
    custom = _env("NOVA_MODEL_PREFERENCES")
    if custom:
        return [p.strip().lower() for p in custom.split(",") if p.strip()]
    return DEFAULT_MODEL_PREFERENCES


def choose_best_model(model_ids: List[str], preferences: Optional[List[str]] = None) -> Optional[str]:
    """Pick the highest-preference chat model from ``model_ids``."""
    prefs = preferences or model_preferences()
    chat_models = [m for m in model_ids if m and not any(h in m.lower() for h in _NON_CHAT_HINTS)]
    for pref in prefs:
        matches = sorted((m for m in chat_models if pref in m.lower()), key=len)
        if matches:
            return matches[0]
    return chat_models[0] if chat_models else None


def list_nova_models() -> List[str]:
    """Return the model ids the configured Nova gateway exposes."""
    from openai import OpenAI

    client = OpenAI(api_key=_env("NOVA_API_KEY"), base_url=_env("NOVA_BASE_URL", DEFAULT_NOVA_BASE_URL))
    return sorted(m.id for m in client.models.list())


@lru_cache(maxsize=1)
def resolve_nova_model() -> str:
    """``NOVA_MODEL`` if set, otherwise the best model the gateway lists."""
    configured = _env("NOVA_MODEL")
    if configured:
        return configured
    try:
        models = list_nova_models()
    except Exception as e:  # network/auth problem: fail loudly with a useful message
        raise ValueError(
            "NOVA_MODEL is not set and the model list could not be fetched from "
            f"{_env('NOVA_BASE_URL', DEFAULT_NOVA_BASE_URL)}: {e}. "
            "Set NOVA_MODEL in .env (run `python list_models.py` to see the options)."
        ) from e
    chosen = choose_best_model(models)
    if not chosen:
        raise ValueError("The Nova gateway returned no chat models. Set NOVA_MODEL explicitly in .env.")
    logger.info("Nova API: auto-selected model %s (from %d available)", chosen, len(models))
    return chosen


def get_chat_model(temperature: float = 0.2):
    """Build a LangChain chat model for the configured provider."""
    provider = get_provider()
    if provider == "nova":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=resolve_nova_model(),
            api_key=_env("NOVA_API_KEY"),
            base_url=_env("NOVA_BASE_URL", DEFAULT_NOVA_BASE_URL),
            temperature=temperature,
            timeout=float(_env("LLM_TIMEOUT_SECONDS", "120")),
            max_retries=2,
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
    return ChatGoogleGenerativeAI(
        model=_env("GEMINI_MODEL", "gemini-3.6-flash"),
        google_api_key=api_key,
        temperature=temperature,
    )


def describe_model() -> str:
    """Human-readable 'provider/model' string for logs and the UI."""
    try:
        provider = get_provider()
        if provider == "nova":
            return f"nova/{resolve_nova_model()}"
        return f"gemini/{_env('GEMINI_MODEL', 'gemini-2.5-flash')}"
    except Exception as e:
        return f"unconfigured ({e})"


# ---------------------------------------------------------------------------
# Structured output that works on gateways with or without tool-calling support
# ---------------------------------------------------------------------------

def _text_of(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def extract_json(text: str) -> Any:
    """Parse the first JSON object/array in ``text`` (tolerates code fences and chatter)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = min([i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("No JSON found in model response")
    depth = 0
    opener = cleaned[start]
    closer = "}" if opener == "{" else "]"
    for i in range(start, len(cleaned)):
        if cleaned[i] == opener:
            depth += 1
        elif cleaned[i] == closer:
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise ValueError("Unterminated JSON in model response")


def invoke_structured(llm, prompt: Any, schema: Type[T]) -> T:
    """Get a ``schema`` instance from ``llm``.

    Tries the provider's native structured-output support first; if the gateway
    or model does not support it, falls back to asking for JSON and parsing it.
    """
    try:
        result = llm.with_structured_output(schema).invoke(prompt)
        if isinstance(result, schema):
            return result
        if isinstance(result, dict):
            return schema.model_validate(result)
        logger.warning("Structured output returned %s; falling back to JSON parsing", type(result).__name__)
    except Exception as e:
        logger.warning("Native structured output unavailable (%s); falling back to JSON parsing", e)

    json_prompt = (
        f"{prompt}\n\nRespond with ONLY a JSON object (no prose, no code fences) that matches this JSON schema:\n"
        f"{json.dumps(schema.model_json_schema())}"
    )
    response = llm.invoke(json_prompt)
    return schema.model_validate(extract_json(_text_of(response)))
