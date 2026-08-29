from typing import TypedDict
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
load_dotenv()


# ==========================================
# 1. SETUP GEMINI AI
# ==========================================
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash", 
    google_api_key= os.getenv("GOOGLE_API_KEY")
)

# ==========================================
# 2. HELPER & STATE DEFINITION
# ==========================================
def extract_text(content) -> str:
    """Safely extracts text whether LangChain returns a string or a list of blocks."""
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content)

class SocraticState(TypedDict):
    question: str
    question_type: str       
    correct_answer: str      
    student_answer: str
    attempt_count: int       
    is_correct: bool         
    feedback: str            
    status: str              

# ==========================================
# 3. NODE 1: EVALUATE THE ANSWER
# ==========================================
def evaluate_answer(state: SocraticState):
    # Safely convert to string before stripping in case of unexpected input types
    student_ans = str(state.get("student_answer", "")).strip().lower()
    correct_ans = str(state.get("correct_answer", "")).strip().lower()
    
    if state.get("question_type") == "mcq":
        is_correct = (student_ans == correct_ans)
        return {"is_correct": is_correct}
    else:
        eval_prompt = f"""
        You are an expert academic evaluator.
        
        Question: {state['question']}
        Grading Rubric / Correct Answer: {state['correct_answer']}
        Student's Answer: {state['student_answer']}
        
        Evaluate if the student's answer demonstrates a correct understanding of the rubric.
        Be lenient on typos, but strict on core concepts.
        
        Respond ONLY with a valid JSON object matching this schema:
        {{
            "is_correct": boolean,
            "reasoning": "string explaining the grade"
        }}
        """
        response = llm.invoke(eval_prompt)
        
        # Safely extract text from the LangChain response object
        raw_text = extract_text(response.content)
        
        try:
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            parsed_result = json.loads(clean_json)
            return {"is_correct": parsed_result["is_correct"]}
        except Exception as e:
            print(f"Parsing error: {e}")
            return {"is_correct": False}

# ==========================================
# 4. NODE 2: GENERATE HINT OR EXPLANATION
# ==========================================
def generate_feedback(state: SocraticState):
    is_correct = state.get("is_correct", False)
    attempts = state.get("attempt_count", 1)
    
    if is_correct or attempts >= 3:
        explanation_prompt = f"""
        Question: {state['question']}
        Correct Answer: {state['correct_answer']}
        Student Answer: {state['student_answer']}
        
        The student is {'correct' if is_correct else 'incorrect after maximum attempts'}.
        Provide a concise, encouraging final explanation of the correct concept.
        """
        response = llm.invoke(explanation_prompt)
        
        # Safely extract text before stripping
        raw_text = extract_text(response.content)
        return {"feedback": raw_text.strip(), "status": "completed"}
    
    else:
        hint_prompt = f"""
        You are a Socratic tutor. The student answered incorrectly.
        
        Question: {state['question']}
        Correct Answer: {state['correct_answer']}
        Student's Wrong Answer: {state['student_answer']}
        Current Attempt: {attempts} out of 3
        
        INSTRUCTIONS:
        1. DO NOT reveal the correct answer.
        2. DO NOT say "No" or "Wrong". Start by validating any part of their answer that makes sense.
        3. Ask exactly ONE thought-provoking question to guide them toward the correct concept.
        4. Keep it under 2 sentences.
        """
        response = llm.invoke(hint_prompt)
        
        # Safely extract text before stripping
        raw_text = extract_text(response.content)
        return {"feedback": raw_text.strip(), "status": "retry"}

# ==========================================
# 5. BUILD THE LANGGRAPH WORKFLOW
# ==========================================
workflow = StateGraph(SocraticState)

workflow.add_node("evaluate", evaluate_answer)
workflow.add_node("generate_feedback", generate_feedback)

workflow.set_entry_point("evaluate")
workflow.add_edge("evaluate", "generate_feedback")
workflow.add_edge("generate_feedback", END)

socratic_agent = workflow.compile()


# ==========================================
# 6. TEST THE AGENT
# ==========================================
if __name__ == "__main__":
    print("Initializing MCQ test...\n")
    
    # ---------------------------------------------------------
    # MCQ TEST CASE
    # ---------------------------------------------------------
    mcq_state = {
        "question": "Which algorithmic approach is used for spaced repetition in AdaptEd? \nA) Bubble Sort \nB) SM-2 / Leitner \nC) K-Means Clustering \nD) Binary Search",
        "question_type": "mcq",
        "correct_answer": "b",           # The correct option
        "student_answer": "c",           # The student guesses incorrectly
        "attempt_count": 1,
        "is_correct": False, 
        "feedback": "",
        "status": ""
    }
    
    print("--- MCQ ATTEMPT 1 (Student guesses C - Wrong) ---")
    mcq_result = socratic_agent.invoke(mcq_state)
    print(f"Graded as Correct?: {mcq_result['is_correct']}")
    print(f"Status returned to Orchestrator: {mcq_result['status']}")
    print(f"Agent Feedback (Hint): {mcq_result['feedback']}\n")
    
    print("--- MCQ ATTEMPT 2 (Student guesses B - Right) ---")
    mcq_state["attempt_count"] = 2
    mcq_state["student_answer"] = "b"    # Student corrects their answer
    
    mcq_result_2 = socratic_agent.invoke(mcq_state)
    print(f"Graded as Correct?: {mcq_result_2['is_correct']}")
    print(f"Status returned to Orchestrator: {mcq_result_2['status']}")
    print(f"Agent Feedback (Explanation): {mcq_result_2['feedback']}")