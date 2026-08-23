import os
import re
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_core.documents import Document

from backend.services.chunker import split_documents
from backend.services.document_loader import load_pdf
from backend.services.metadata_tagger import tag_chunk
from backend.services.vector_store import add_documents
from backend.services.vector_store import search as vs_search

# Load environment variables
load_dotenv()


class ContentIngestionAgent:
    """Agent in charge of loading, cleaning, chunking, tagging, embedding,

    and storing documents into ChromaDB.
    """

    def __init__(self) -> None:
        pass

    def clean_text(self, text: str) -> str:
        """Cleans extracted text by normalizing spaces and newlines."""
        if not text:
            return ""
        # Replace multiple newlines with single newline
        text = re.sub(r"\n+", "\n", text)
        # Replace multiple spaces/tabs with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Strip trailing spaces on each line
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join([line for line in lines if line]).strip()

    def ingest(self, file_path: str) -> Dict[str, Any]:
        """Runs the content ingestion pipeline on a local PDF file.

        Args:
            file_path: The local path to the PDF.

        Returns:
            A summary dictionary containing status, page count, and chunk counts.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        # 1. Load PDF
        documents = load_pdf(file_path)
        pages_count = len(documents)

        # 2. Clean text
        cleaned_documents = []
        for doc in documents:
            cleaned_text = self.clean_text(doc.page_content)
            if cleaned_text:  # Only ingest pages with content
                doc.page_content = cleaned_text
                cleaned_documents.append(doc)

        if not cleaned_documents:
            raise ValueError(f"No parseable text content found in {file_path}")

        # 3. Split into chunks
        chunks = split_documents(cleaned_documents)

        # 4. Tag chunks with topic/difficulty/bloom_level
        for chunk in chunks:
            tags = tag_chunk(chunk.page_content)
            chunk.metadata.update(tags)

        # 5. Embed and store in ChromaDB
        add_documents(chunks)

        return {
            "status": "success",
            "filename": os.path.basename(file_path),
            "pages": pages_count,
            "chunks_created": len(chunks),
            "chunks_stored": len(chunks),
        }

    def search(self, query: str, k: int = 5) -> List[Document]:
        """Searches the persistent database for chunks related to a query.

        Args:
            query: The search string.
            k: The number of documents to retrieve.

        Returns:
            A list of Document objects matching the query.
        """
        return vs_search(query, k=k)
