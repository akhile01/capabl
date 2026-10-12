"""Prints the chat models your Clean API / Nova API gateway exposes and which one AdaptEd
will use. Run after filling CLEAN_API_KEY in .env:

    python list_models.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.llm import choose_best_model, list_nova_models, _env, DEFAULT_NOVA_BASE_URL

if __name__ == "__main__":
    api_key = _env("CLEAN_API_KEY") or _env("NOVA_API_KEY")
    if not api_key:
        sys.exit("CLEAN_API_KEY (or NOVA_API_KEY) is not set in .env")
    base = _env("CLEAN_BASE_URL") or _env("NOVA_BASE_URL", DEFAULT_NOVA_BASE_URL)
    print(f"Fetching models from {base} ...")
    try:
        models = list_nova_models()
    except Exception as e:
        sys.exit(f"Could not list models: {e}\nCheck CLEAN_BASE_URL and CLEAN_API_KEY in .env.")
    for m in models:
        print(f"  {m}")
    pinned = _env("CLEAN_MODEL") or _env("NOVA_MODEL")
    print()
    if pinned:
        print(f"Model is pinned to: {pinned}")
    else:
        print(f"Auto-selected (best available): {choose_best_model(models)}")
        print("Pin a different one with CLEAN_MODEL=<id> in .env")
