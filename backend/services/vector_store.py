"""Lightweight persistent document store used for retrieval.

The original stub re-created an empty in-memory store on every call, so chunks
ingested from a PDF were discarded immediately and question generation always
reported "No context found". This implementation keeps one shared store per
process, persists it to ``database/chromadb/store.json`` so uploads survive a
server restart, and ranks chunks by keyword overlap with the query.
"""
import json
import os
import re
import threading
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# Store database in capabl/database/chromadb
DB_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "database",
        "chromadb",
    )
)
STORE_FILE = os.path.join(DB_DIR, "store.json")

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "be",
    "with", "by", "as", "at", "from", "that", "this", "it", "its", "into", "than",
}


from backend.services.embeddings import get_embeddings_model


def _tokens(text: str) -> List[str]:
    return [t for t in _WORD.findall((text or "").lower()) if t not in _STOPWORDS]


class DocumentStore:
    """Process-wide, file-backed collection of text chunks."""

    def __init__(self, collection_name: str, persist_directory: str, embedding_function=None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self._path = os.path.join(persist_directory, "store.json")
        self._lock = threading.RLock()
        self._docs: Dict[str, Dict] = {}
        self._load()


    # ---- persistence -----------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._docs = {d["id"]: d for d in data.get("documents", []) if "id" in d}
        except Exception as e:  # corrupt file: start empty rather than crash the app
            print(f"Warning: could not read {self._path}: {e}")
            self._docs = {}

    def _save(self) -> None:
        os.makedirs(self.persist_directory, exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"collection": self.collection_name, "documents": list(self._docs.values())}, f)
        os.replace(tmp, self._path)

    # ---- API used by the agents ----------------------------------------
    def add_documents(self, docs: List[Document], ids: Optional[List[str]] = None) -> None:
        ids = ids or [None] * len(docs)
        with self._lock:
            for i, (doc, doc_id) in enumerate(zip(docs, ids)):
                metadata = dict(getattr(doc, "metadata", {}) or {})
                doc_id = doc_id or metadata.get("chunk_id") or f"chunk_{len(self._docs) + i}"
                metadata.setdefault("chunk_id", doc_id)
                self._docs[doc_id] = {"id": doc_id, "page_content": doc.page_content, "metadata": metadata}
            self._save()

    def get(self, ids: List[str]) -> Dict[str, List[str]]:
        with self._lock:
            return {"ids": [i for i in ids if i in self._docs]}

    def count(self) -> int:
        return len(self._docs)

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Rank chunks by keyword overlap. Score is a distance: 0 = best match."""
        q_tokens = set(_tokens(query))
        q_lower = (query or "").lower().strip()
        scored = []
        with self._lock:
            for d in self._docs.values():
                content = d["page_content"]
                meta = d.get("metadata", {})
                c_tokens = set(_tokens(content)) | set(_tokens(str(meta.get("topic", ""))))
                overlap = len(q_tokens & c_tokens) / len(q_tokens) if q_tokens else 0.0
                if q_lower and q_lower in content.lower():
                    overlap = max(overlap, 1.0)
                scored.append((1.0 - overlap, d))
        scored.sort(key=lambda s: s[0])
        results = []
        for distance, d in scored[:k]:
            results.append((Document(page_content=d["page_content"], metadata=dict(d["metadata"])), distance))
        return results

    def delete_collection(self) -> None:
        with self._lock:
            self._docs.clear()
            if os.path.exists(self._path):
                os.remove(self._path)


# Backwards-compatible alias: older code and tests refer to the store as "Chroma".
Chroma = DocumentStore

_STORE: Optional[DocumentStore] = None
_STORE_LOCK = threading.Lock()


def get_vector_store() -> DocumentStore:
    """Returns the shared document store (created on first use or reloaded if DB_DIR changed)."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is None or _STORE.persist_directory != DB_DIR:
            _STORE = DocumentStore(
                collection_name="adapted_knowledge",
                persist_directory=DB_DIR,
                embedding_function=get_embeddings_model(),
            )
        return _STORE


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _add_batch_with_retry(vector_store: DocumentStore, batch_docs: List[Document], batch_ids: List[str]) -> None:
    """Helper function to add a single batch of documents with retry logic."""
    emb_model = getattr(vector_store, "embedding_function", None) or get_embeddings_model()
    if emb_model and hasattr(emb_model, "embed_documents"):
        texts = [doc.page_content for doc in batch_docs]
        emb_model.embed_documents(texts)
    vector_store.add_documents(batch_docs, ids=batch_ids)



def add_documents(documents: List[Document]) -> None:
    """Adds a list of Document objects to the store, skipping chunks already present."""
    if not documents:
        return

    vector_store = get_vector_store()

    ids = []
    for i, doc in enumerate(documents):
        chunk_id = doc.metadata.get("chunk_id")
        if not chunk_id:
            chunk_id = f"chunk_{i}"
            doc.metadata["chunk_id"] = chunk_id
        ids.append(chunk_id)

    existing_ids = set()
    try:
        existing = vector_store.get(ids=ids)
        if existing and existing.get("ids"):
            existing_ids = set(existing["ids"])
    except Exception as e:
        print(f"Non-fatal warning: failed to retrieve existing IDs: {e}")

    docs_to_add = []
    ids_to_add = []
    for doc, chunk_id in zip(documents, ids):
        if chunk_id not in existing_ids:
            docs_to_add.append(doc)
            ids_to_add.append(chunk_id)

    if not docs_to_add:
        print("All chunks already exist in vector store. Skipping ingestion.")
        return

    print(f"Adding {len(docs_to_add)} new chunks to the document store (skipped {len(existing_ids)} already existing chunks).")

    batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))
    for j in range(0, len(docs_to_add), batch_size):
        _add_batch_with_retry(vector_store, docs_to_add[j : j + batch_size], ids_to_add[j : j + batch_size])


def search(query: str, k: int = 5) -> List[Document]:
    """Returns the ``k`` chunks most relevant to ``query`` (empty list if nothing is ingested)."""
    vector_store = get_vector_store()
    docs = []
    for doc, score in vector_store.similarity_search_with_score(query, k=k):
        doc.metadata["score"] = score
        docs.append(doc)
    return docs


def delete_collection() -> None:
    """Deletes every stored chunk and resets the store."""
    global _STORE
    with _STORE_LOCK:
        if _STORE is not None:
            _STORE.delete_collection()
            _STORE = None
        else:
            DocumentStore(collection_name="adapted_knowledge", persist_directory=DB_DIR).delete_collection()

