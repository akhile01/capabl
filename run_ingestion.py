import os
import sys
from dotenv import load_dotenv

# Ensure the backend directory is in the sys.path so 'import agents' works correctly
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
)

# Load environment variables
load_dotenv()

# Check for API key
api_key = os.getenv("GEMINI_API_KEY")

from agents.content_ingestion import ContentIngestionAgent


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not api_key or api_key in ["PASTE_NEW_KEY_HERE", "your_gemini_api_key_here", ""]:
        print("ERROR: GEMINI_API_KEY is not set to a valid key in environment variables.")
        print("Please configure your .env file with your actual Gemini API key before running this script.")
        sys.exit(1)

    pdf_path = "data/uploads/UNIT-5.pdf"
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF file not found at: {pdf_path}")
        sys.exit(1)

    print("Instantiating ContentIngestionAgent...")
    agent = ContentIngestionAgent()

    print(f"Ingesting PDF: {pdf_path}...")
    try:
        summary = agent.ingest(pdf_path)
        print("\n=== INGESTION SUCCESSFUL ===")
        print(f"Status: {summary.get('status')}")
        print(f"Filename: {summary.get('filename')}")
        print(f"Total Pages: {summary.get('pages')}")
        print(f"Chunks Created: {summary.get('chunks_created')}")
        print(f"Chunks Stored: {summary.get('chunks_stored')}")
        print("============================\n")
    except Exception as e:
        print(f"ERROR: Ingestion failed: {e}")
        sys.exit(1)

    query = "What is a B+ tree?"
    print(f"Searching for query: '{query}'...")
    try:
        results = agent.search(query, k=5)
        print(f"\n=== RETRIEVAL RESULTS (k={len(results)}) ===")
        for i, doc in enumerate(results):
            score = doc.metadata.get("score", "N/A")
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "unknown")
            topic = doc.metadata.get("topic", "unknown")
            difficulty = doc.metadata.get("difficulty", "unknown")
            bloom = doc.metadata.get("bloom_level", "unknown")

            print(f"\nResult {i+1}:")
            print(f"- Source: {source} (Page {page})")
            print(
                f"- Metadata: Topic={topic}, Difficulty={difficulty}, Bloom Level={bloom}"
            )
            print(f"- Distance Score (Chroma): {score}")
            print("- Content Chunk:")
            indented_content = "\n".join(
                "  " + line for line in doc.page_content.strip().split("\n")
            )
            print(indented_content)
        print("==================================\n")
    except Exception as e:
        print(f"ERROR: Search failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
