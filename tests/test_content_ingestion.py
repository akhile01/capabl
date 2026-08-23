import os
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.documents import Document

from backend.agents.content_ingestion import ContentIngestionAgent
from backend.services.chunker import split_documents
from backend.services.document_loader import load_pdf
from backend.services.embeddings import embed_documents, embed_query
from backend.services.metadata_tagger import tag_chunk
from backend.services.vector_store import (
    add_documents,
    delete_collection,
    search,
)


@patch("backend.services.document_loader.PdfReader")
def test_pdf_loading(mock_reader_class, tmp_path):
    # Setup mock reader with mock page
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page content. Normalization is a database design technique."
    mock_reader.pages = [mock_page]
    mock_reader_class.return_value = mock_reader

    # Create dummy empty file to satisfy os.path.exists
    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_text("")

    docs = load_pdf(str(dummy_pdf))
    assert len(docs) == 1
    assert (
        docs[0].page_content
        == "Page content. Normalization is a database design technique."
    )
    assert docs[0].metadata["source"] == "test.pdf"
    assert docs[0].metadata["page"] == 1


def test_chunk_creation():
    doc1 = Document(
        page_content="Page 1: Normalization is key to database design.",
        metadata={"source": "dbms.pdf", "page": 1},
    )
    # Ensure RecursiveCharacterTextSplitter splits documents correctly
    chunks = split_documents([doc1], chunk_size=30, chunk_overlap=5)

    assert len(chunks) > 1
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert "page" in chunk.metadata
        assert "chunk_id" in chunk.metadata
        assert chunk.metadata["source"] == "dbms.pdf"
        assert chunk.metadata["page"] == 1


@patch("backend.services.embeddings.GoogleGenerativeAIEmbeddings")
def test_embeddings(mock_embeddings_class):
    mock_instance = MagicMock()
    mock_instance.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_instance

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        embeddings = embed_documents(["hello"])
        assert len(embeddings) == 1
        assert embeddings[0] == [0.1, 0.2, 0.3]

        query_emb = embed_query("hello")
        assert query_emb == [0.1, 0.2, 0.3]


@patch("backend.services.metadata_tagger.ChatGoogleGenerativeAI")
def test_tagging(mock_chat_class):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"topic": "Normalization", "difficulty": "medium", "bloom_level": "understand"}'
    mock_instance.invoke.return_value = mock_response
    mock_chat_class.return_value = mock_instance

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        tags = tag_chunk("Which normal form removes partial dependency?")
        assert tags["topic"] == "Normalization"
        assert tags["difficulty"] == "medium"
        assert tags["bloom_level"] == "understand"


@patch("backend.services.embeddings.GoogleGenerativeAIEmbeddings")
def test_vector_store(mock_embeddings_class, tmp_path):
    # Set the DB_DIR directly on the module so it is a valid string/path
    import backend.services.vector_store

    backend.services.vector_store.DB_DIR = str(tmp_path / "test_chroma")

    # Mock embeddings to return 3 dimensions
    mock_instance = MagicMock()
    mock_instance.embed_documents.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
    mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_instance

    doc1 = Document(
        page_content="Normalization is key.",
        metadata={"chunk_id": "c1", "source": "test.pdf", "page": 1},
    )
    doc2 = Document(
        page_content="SQL query execution.",
        metadata={"chunk_id": "c2", "source": "test.pdf", "page": 1},
    )

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        delete_collection()
        add_documents([doc1, doc2])

        results = search("Normalization", k=1)
        assert len(results) == 1
        assert "Normalization" in results[0].page_content
        assert results[0].metadata["chunk_id"] == "c1"


@patch("backend.services.embeddings.GoogleGenerativeAIEmbeddings")
@patch("backend.services.metadata_tagger.ChatGoogleGenerativeAI")
@patch("backend.services.document_loader.PdfReader")
def test_agent_end_to_end(
    mock_reader_class,
    mock_chat_class,
    mock_embeddings_class,
    tmp_path,
):
    # Set the DB_DIR directly on the module so it is a valid string/path
    import backend.services.vector_store

    backend.services.vector_store.DB_DIR = str(
        tmp_path / "test_chroma_agent"
    )

    # Mock reader
    mock_reader = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Normalization removes database redundancy."
    mock_reader.pages = [mock_page]
    mock_reader_class.return_value = mock_reader

    # Mock LLM
    mock_chat = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"topic": "Normalization", "difficulty": "medium", "bloom_level": "understand"}'
    mock_chat.invoke.return_value = mock_response
    mock_chat_class.return_value = mock_chat

    # Mock embeddings
    mock_embeddings = MagicMock()
    mock_embeddings.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_embeddings

    # Create dummy empty file to satisfy load check
    dummy_pdf = tmp_path / "dbms.pdf"
    dummy_pdf.write_text("")

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        agent = ContentIngestionAgent()
        result = agent.ingest(str(dummy_pdf))

        assert result["status"] == "success"
        assert result["filename"] == "dbms.pdf"
        assert result["pages"] == 1
        assert result["chunks_created"] == 1
        assert result["chunks_stored"] == 1

        # Check retrieval
        retrieved = agent.search("Normalization", k=1)
        assert len(retrieved) == 1
        assert "redundancy" in retrieved[0].page_content
        assert retrieved[0].metadata["topic"] == "Normalization"
        assert retrieved[0].metadata["difficulty"] == "medium"
        assert retrieved[0].metadata["bloom_level"] == "understand"


def test_deterministic_chunk_ids():
    doc = Document(
        page_content="Test deterministic chunk content.",
        metadata={"source": "test.pdf", "page": 1},
    )
    chunks = split_documents([doc])

    assert len(chunks) == 1
    chunk = chunks[0]
    chunk_id_1 = chunk.metadata["chunk_id"]

    # Run again with same content
    chunks_2 = split_documents([doc])
    chunk_id_2 = chunks_2[0].metadata["chunk_id"]

    assert chunk_id_1 == chunk_id_2
    assert "test.pdf_p1_c0_" in chunk_id_1

    # Check that MD5 hash snippet is in the chunk_id
    import hashlib

    expected_hash = (
        hashlib.md5(doc.page_content.encode("utf-8")).hexdigest()[:12]
    )
    assert expected_hash in chunk_id_1


@patch("backend.services.vector_store.DB_DIR")
@patch("backend.services.embeddings.GoogleGenerativeAIEmbeddings")
def test_vector_store_batching_and_deduplication(
    mock_embeddings_class, mock_db_dir, tmp_path
):
    import backend.services.vector_store

    backend.services.vector_store.DB_DIR = str(
        tmp_path / "test_chroma_batch"
    )

    mock_instance = MagicMock()
    mock_instance.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_instance

    doc1 = Document(
        page_content="Chunk 1",
        metadata={"chunk_id": "c1", "source": "test.pdf", "page": 1},
    )
    doc2 = Document(
        page_content="Chunk 2",
        metadata={"chunk_id": "c2", "source": "test.pdf", "page": 1},
    )

    with patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "fake-key", "EMBEDDING_BATCH_SIZE": "1"},
    ):
        delete_collection()
        # Add doc1 first
        add_documents([doc1])

        # Reset mock call count to check deduplication
        mock_instance.embed_documents.reset_mock()

        # Add doc1 and doc2. doc1 already exists, so only doc2 should be embedded and added
        add_documents([doc1, doc2])

        # Embed documents should only be called once (for doc2)
        assert mock_instance.embed_documents.call_count == 1

        results = search("Chunk", k=2)
        assert len(results) == 2


@patch("backend.services.vector_store.DB_DIR")
@patch("backend.services.embeddings.GoogleGenerativeAIEmbeddings")
def test_vector_store_retry_handling(
    mock_embeddings_class, mock_db_dir, tmp_path
):
    import backend.services.vector_store

    backend.services.vector_store.DB_DIR = str(
        tmp_path / "test_chroma_retry"
    )

    mock_instance = MagicMock()
    # First call to embed_documents fails with RateLimit/429 exception, second call succeeds
    mock_instance.embed_documents.side_effect = [
        Exception("429 Resource Exhausted"),
        [[0.1, 0.2, 0.3]],
    ]
    mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_instance

    doc1 = Document(
        page_content="Chunk 1",
        metadata={"chunk_id": "c1", "source": "test.pdf", "page": 1},
    )

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
        delete_collection()

        # Patch the wait time to make the retry run fast
        with patch("tenacity.nap.time.sleep", return_value=None):
            add_documents([doc1])

        # Verify that it succeeded after retrying (meaning embed_documents was called twice)
        assert mock_instance.embed_documents.call_count == 2
        results = search("Chunk 1", k=1)
        assert len(results) == 1
