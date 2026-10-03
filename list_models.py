"""Prints the chat models your Nova API gateway exposes and which one AdaptEd
will use. Run after filling NOVA_API_KEY / NOVA_BASE_URL in .env:

    python list_models.py
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.llm import choose_best_model, list_nova_models, _env, DEFAULT_NOVA_BASE_URL

if __name__ == "__main__":
    if not _env("NOVA_API_KEY"):
        sys.exit("NOVA_API_KEY is not set in .env")
    base = _env("NOVA_BASE_URL", DEFAULT_NOVA_BASE_URL)
    print(f"Fetching models from {base} ...")
    try:
        models = list_nova_models()
    except Exception as e:
        sys.exit(f"Could not list models: {e}\nCheck NOVA_BASE_URL and NOVA_API_KEY in .env.")
    for m in models:
        print(f"  {m}")
    pinned = _env("NOVA_MODEL")
    print()
    if pinned:
        print(f"NOVA_MODEL is pinned to: {pinned}")
    else:
        print(f"Auto-selected (best available): {choose_best_model(models)}")
        print("Pin a different one with NOVA_MODEL=<id> in .env")
