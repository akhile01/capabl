import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
load_dotenv()

from agents.content_ingestion import ContentIngestionAgent
from agents.question_generation import QuestionGenerationAgent
from agents.socratic_agent import SocraticEvaluationAgent

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pdf_path = "data/uploads/UNIT-5.pdf"
    
    print("=== 1. INGESTING ===")
    ingestion_agent = ContentIngestionAgent()
    summary = ingestion_agent.ingest(pdf_path)
    print(f"Ingested {pdf_path}. Chunks stored: {summary.get('chunks_stored')}")
    
    print("\n=== 2. GENERATING QUESTIONS ===")
    gen_agent = QuestionGenerationAgent()
    
    topics = [
        {"topic": "Transaction states", "difficulty": "easy"}
    ]
    
    generated_q = None
    for req in topics:
        print(f"\nGenerating {req['difficulty']} question about {req['topic']}...")
        result = gen_agent.generate_questions(topic=req["topic"], count=1, difficulty=req["difficulty"])
        if result.get("questions"):
            q = result["questions"][0]
            print(f"Question: {q.question_text}")
            print(f"Options: {q.options}")
            print(f"Correct Answer: {q.correct_answer} (Index {q.correct_answer_index})")
            generated_q = q
        else:
            print("Failed to generate.")

    if generated_q:
        print("\n=== 3. SOCRATIC EVALUATION ===")
        eval_agent = SocraticEvaluationAgent()
        
        # Simulate an incorrect answer
        student_ans = generated_q.options[(generated_q.correct_answer_index + 1) % len(generated_q.options)]
        
        print(f"Student Answer (Simulated Incorrect): {student_ans}")
        eval_result = eval_agent.evaluate(
            question=generated_q.question_text,
            question_type="mcq",
            correct_answer=generated_q.correct_answer,
            student_answer=student_ans,
            attempt_count=1
        )
        print(f"Evaluation Result:")
        print(json.dumps(eval_result, indent=2))

if __name__ == "__main__":
    main()
