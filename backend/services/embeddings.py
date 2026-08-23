import os
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Initializes and returns the Google Generative AI embeddings model.

    Reads the API key from GEMINI_API_KEY, GOOGLE_API_KEY, or API_KEY env variables.

    Returns:
        GoogleGenerativeAIEmbeddings instance.

    Raises:
        ValueError: If no API key is found in environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables."
        )

    # Use standard text-embedding-004 model
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", google_api_key=api_key
    )


def embed_documents(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a list of document texts.

    Args:
        texts: A list of string texts.

    Returns:
        A list of embedding vectors.
    """
    model = get_embeddings_model()
    return model.embed_documents(texts)


def embed_query(text: str) -> List[float]:
    """Generates an embedding for a query text.

    Args:
        text: A single string query.

    Returns:
        An embedding vector.
    """
    model = get_embeddings_model()
    return model.embed_query(text)
