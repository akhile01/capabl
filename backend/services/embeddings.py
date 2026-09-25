import os
import hashlib
from typing import List

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

def get_embeddings_model() -> DummyEmbeddings:
    """Placeholder embeddings model that returns deterministic vectors."""
    return DummyEmbeddings()

def embed_documents(texts: List[str]) -> List[List[float]]:
    model = get_embeddings_model()
    return model.embed_documents(texts)

def embed_query(text: str) -> List[float]:
    model = get_embeddings_model()
    return model.embed_query(text)
