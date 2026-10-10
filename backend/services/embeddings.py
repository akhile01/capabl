import os
import hashlib
from typing import List

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except Exception:
    class GoogleGenerativeAIEmbeddings:
        pass

# Simple deterministic embedding using SHA256 hash, returns 128‑dim float vector
def _hash_to_vector(text: str, dim: int = 128) -> List[float]:
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    # Repeat digest to fill required bytes
    repeats = (dim * 4) // len(digest) + 1
    full = (digest * repeats)[: dim * 4]
    vec = []
    for i in range(0, len(full), 4):
        chunk = int.from_bytes(full[i:i+4], 'big')
        vec.append(chunk / 0xffffffff)
    return vec[:dim]

class DummyEmbeddings:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_hash_to_vector(t) for t in texts]
    def embed_query(self, text: str) -> List[float]:
        return _hash_to_vector(text)

def get_embeddings_model():
    """Initializes and returns the Google Generative AI embeddings model if an API key is available,
    otherwise falls back to deterministic dummy embeddings for offline development.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            return GoogleGenerativeAIEmbeddings(
                model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
                google_api_key=api_key,
            )
        except Exception:
            pass
    return DummyEmbeddings()

def embed_documents(texts: List[str]) -> List[List[float]]:
    model = get_embeddings_model()
    return model.embed_documents(texts)

def embed_query(text: str) -> List[float]:
    model = get_embeddings_model()
    return model.embed_query(text)

