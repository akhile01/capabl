import os
from typing import List
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.services.embeddings import get_embeddings_model

# Load environment variables
load_dotenv()

# Store database in capabl/database/chromadb
DB_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "database",
        "chromadb",
    )
)


def get_vector_store() -> Chroma:
    """Initializes and returns the Chroma vector store instance."""
    embeddings = get_embeddings_model()
    return Chroma(
        collection_name="adapted_knowledge",
        embedding_function=embeddings,
        persist_directory=DB_DIR,
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _add_batch_with_retry(vector_store: Chroma, batch_docs: List[Document], batch_ids: List[str]) -> None:
    """Helper function to add a single batch of documents to Chroma with retry logic."""
    vector_store.add_documents(batch_docs, ids=batch_ids)


def add_documents(documents: List[Document]) -> None:
    """Adds a list of Document objects to the Chroma vector store.

    Checks for existing IDs to avoid re-embedding. Remaining documents are
    embedded and added in batches with retry logic.

    Args:
        documents: A list of Document objects.
    """
    if not documents:
        return

    vector_store = get_vector_store()

    # Extract unique IDs from document metadata
    ids = []
    for i, doc in enumerate(documents):
        chunk_id = doc.metadata.get("chunk_id")
        if not chunk_id:
            chunk_id = f"chunk_{i}"
            doc.metadata["chunk_id"] = chunk_id
        ids.append(chunk_id)

    # Filter out documents that already exist in Chroma
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

    print(
        f"Adding {len(docs_to_add)} new chunks to ChromaDB (skipped {len(existing_ids)} already existing chunks)."
    )

    # Configurable batch size
    batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))

    # Add documents in batches with retry logic
    for j in range(0, len(docs_to_add), batch_size):
        batch_docs = docs_to_add[j : j + batch_size]
        batch_ids = ids_to_add[j : j + batch_size]
        _add_batch_with_retry(vector_store, batch_docs, batch_ids)


def search(query: str, k: int = 5) -> List[Document]:
    """Queries the Chroma vector store using similarity search.

    Args:
        query: The search string query.
        k: The number of results to return.

    Returns:
        A list of matching Document objects.
    """
    vector_store = get_vector_store()
    results_with_score = vector_store.similarity_search_with_score(query, k=k)
    
    docs = []
    for doc, score in results_with_score:
        doc.metadata["score"] = score
        docs.append(doc)
    return docs


def delete_collection() -> None:
    """Deletes the entire Chroma collection."""
    vector_store = get_vector_store()
    vector_store.delete_collection()
