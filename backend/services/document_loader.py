import os
from typing import List
from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(file_path: str) -> List[Document]:
    """Loads a PDF file page by page, extracting text and preserving page metadata.

    Args:
        file_path: The local path to the PDF file.

    Returns:
        A list of Document objects containing extracted text and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF or is empty.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    documents = []
    try:
        reader = PdfReader(file_path)
        if not reader.pages:
            raise ValueError("PDF file is empty")

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            try:
                text = page.extract_text() or ""
                # Preserve metadata
                metadata = {
                    "source": os.path.basename(file_path),
                    "page": page_num,
                }
                documents.append(Document(page_content=text, metadata=metadata))
            except Exception as page_err:
                # Do not crash the entire application because of one bad page
                # Instead, we load a placeholder or print the error
                print(
                    f"Warning: Failed to extract text from page {page_num} in {file_path}: {page_err}"
                )
                # Append a document with empty content but intact metadata to keep count/reference if needed
                metadata = {
                    "source": os.path.basename(file_path),
                    "page": page_num,
                    "error": str(page_err),
                }
                documents.append(Document(page_content="", metadata=metadata))
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Failed to read PDF file {file_path}: {str(e)}")

    return documents
