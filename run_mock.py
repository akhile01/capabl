import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
load_dotenv()

from agents.content_ingestion import ContentIngestionAgent
from agents.question_generation import QuestionGenerationAgent
from model.question import Question
from agents.question_generation import GeneratedMCQ
from langchain_core.documents import Document

class MockQuestionGenerationAgent(QuestionGenerationAgent):
    def _retrieve_context(self, topic: str, k: int = 5):
        print(f"\n[RAG Retrieval] Searching Vector Store for chunks related to: '{topic}'...")
        doc = Document(page_content="Database systems support ACID properties. A transaction is a unit of work.")
        return doc.page_content, [doc]

    def generate_single_question(self, topic: str, difficulty: str, question_type: str = "mcq", bloom_level=None, context_docs=None, prior_questions=None):
        print(f"\n[LLM Generation] Prompting gemini-1.5-flash to generate {difficulty} question on '{topic}'...")
        print(f"[LLM Critique] Critiquing question...")
        print(f"[LLM Critique] - Correctness: Passed")
        print(f"[LLM Critique] - Groundedness: Passed")
        print(f"[LLM Critique] - Distractors: Passed")
        
        from backend.model.question import DifficultyLevel, QuestionType
        return Question(
            subject="Unknown",
            topic=topic,
            difficulty=DifficultyLevel(difficulty),
            bloom_level="Understand",
            question_type=QuestionType.MCQ,
            question_text=f"Which of the following is an ACID property in DBMS related to '{topic}'?",
            options=["Atomicity", "Acceleration", "Aggregation", "Automation"],
            correct_answer="Atomicity",
            correct_answer_index=0,
            explanation="Atomicity ensures that all operations within a work unit are completed successfully; otherwise, the transaction is aborted.",
            source_chunk_id="mock_chunk_0",
            validation_status="validated",
            validation_score=0.95,
            generation_version=1
        )

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=== MOCKED E2E PIPELINE EXECUTION ===\n")
    print("Because your API Key lacks access to the required models, this script mocks the LLM responses to show you how the agent's internal loop works.")
    
    agent = MockQuestionGenerationAgent()
    
    topics = [
        {"topic": "Transaction states", "difficulty": "easy"}
    ]
    
    for req in topics:
        print(f"\n--- Processing Request: {req['topic']} ({req['difficulty']}) ---")
        result = agent.generate_questions(topic=req["topic"], count=1, difficulty=req["difficulty"])
        
        if result.get("questions"):
            q = result["questions"][0]
            print("\n✅ Final Approved Question outputted by Agent:")
            print(f"Question: {q.question_text}")
            print(f"Options: {q.options}")
            print(f"Correct Answer: {q.correct_answer} (Index {q.correct_answer_index})")
            print(f"Explanation: {q.explanation}")
            print(f"Validation Score: {q.validation_score}")
        else:
            print(f"Failed to generate: {result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main()
