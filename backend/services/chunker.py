import hashlib
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[Document]:
    """Splits a list of Documents into chunks using RecursiveCharacterTextSplitter.

    Each chunk retains its metadata (source, page) and receives a unique chunk_id.

    Args:
        documents: A list of input Document objects.
        chunk_size: Target size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.

    Returns:
        A list of split Document objects with chunk_id, source, and page metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = splitter.split_documents(documents)

    # Post-process chunks to assign unique IDs and preserve metadata
    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get("source", "unknown")
        page = chunk.metadata.get("page", 1)

        # Generate a deterministic unique chunk ID incorporating content hash
        content_hash = hashlib.md5(chunk.page_content.encode("utf-8")).hexdigest()[:12]
        chunk_id = f"{source}_p{page}_c{i}_{content_hash}"

        # Assign structured metadata
        chunk.metadata["source"] = source
        chunk.metadata["page"] = page
        chunk.metadata["chunk_id"] = chunk_id

    return chunks
