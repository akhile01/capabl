import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
load_dotenv()

from agents.content_ingestion import ContentIngestionAgent
from agents.question_generation import QuestionGenerationAgent

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pdf_path = "data/uploads/UNIT-5.pdf"
    
    print("=== INGESTING ===")
    ingestion_agent = ContentIngestionAgent()
    summary = ingestion_agent.ingest(pdf_path)
    print(f"Ingested {pdf_path}. Chunks stored: {summary.get('chunks_stored')}")
    
    print("\n=== GENERATING QUESTIONS ===")
    gen_agent = QuestionGenerationAgent()
    
    topics = [
        {"topic": "Transaction states", "difficulty": "easy"},
        {"topic": "ACID properties", "difficulty": "medium"},
        {"topic": "Conflict serializability", "difficulty": "hard"}
    ]
    
    for req in topics:
        print(f"\nGenerating {req['difficulty']} question about {req['topic']}...")
        result = gen_agent.generate_questions(topic=req["topic"], count=1, difficulty=req["difficulty"])
        if result.get("questions"):
            q = result["questions"][0]
            print(f"Question: {q.question_text}")
            print(f"Options: {q.options}")
            print(f"Correct Answer: {q.correct_answer} (Index {q.correct_answer_index})")
            print(f"Explanation: {q.explanation}")
            print(f"Score: {q.validation_score}")
        else:
            print("Failed to generate.")

if __name__ == "__main__":
    main()
