import json
import os
from typing import TypedDict, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# 1. HELPER & STATE DEFINITION
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


class SocraticEvaluationAgent:
    """Agent in charge of evaluating student answers using a Socratic hint-first loop."""
    
    def __init__(self):
        self.llm = self._get_llm()
        self.workflow = self._build_workflow()

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        # Respect existing convention: look for GEMINI_API_KEY first, fallback to GOOGLE_API_KEY
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.")
        return ChatGoogleGenerativeAI(
            model="gemini-3.6-flash", 
            google_api_key=api_key
        )

    # ==========================================
    # NODE 1: EVALUATE THE ANSWER
    # ==========================================
    def _evaluate_answer(self, state: SocraticState):
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
            response = self.llm.invoke(eval_prompt)
            
            raw_text = extract_text(response.content)
            
            try:
                clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                parsed_result = json.loads(clean_json)
                return {"is_correct": parsed_result["is_correct"]}
            except Exception as e:
                print(f"Parsing error: {e}")
                return {"is_correct": False}

    # ==========================================
    # NODE 2: GENERATE HINT OR EXPLANATION
    # ==========================================
    def _generate_feedback(self, state: SocraticState):
        is_correct = state.get("is_correct", False)
        attempts = state.get("attempt_count", 1)
        
        if is_correct or attempts >= 3:
            explanation_prompt = f"""
            Question: {state['question']}
            Correct Answer: {state['correct_answer']}
            Student Answer: {state['student_answer']}
            
            The student is {'correct' if is_correct else 'incorrect after maximum attempts'}.
            Provide a concise, encouraging final explanation of the correct concept.
            Ensure the explanation is highly accurate and easy to understand.
            """
            response = self.llm.invoke(explanation_prompt)
            raw_text = extract_text(response.content)
            return {"feedback": raw_text.strip(), "status": "completed"}
        
        else:
            hint_prompt = f"""
            You are an elite Socratic tutor. The student answered incorrectly or off-topic.
            
            Question: {state['question']}
            Correct Answer: {state['correct_answer']}
            Student's Answer: {state['student_answer']}
            Current Attempt: {attempts} out of 3
            
            CRITICAL INSTRUCTIONS:
            1. UNDER NO CIRCUMSTANCES reveal the exact correct answer, even if the student asks for it directly.
            2. If the student gives an off-topic or joke answer, gently redirect them back to the subject without being mean.
            3. If the student is partially right, validate the correct part first before pointing to what's missing.
            4. Ask exactly ONE guiding question to help them figure it out.
            5. Keep your entire response to a maximum of 2 sentences.
            """
            response = self.llm.invoke(hint_prompt)
            raw_text = extract_text(response.content)
            return {"feedback": raw_text.strip(), "status": "retry"}

    # ==========================================
    # BUILD THE LANGGRAPH WORKFLOW
    # ==========================================
    def _build_workflow(self):
        workflow = StateGraph(SocraticState)

        workflow.add_node("evaluate", self._evaluate_answer)
        workflow.add_node("generate_feedback", self._generate_feedback)

        workflow.set_entry_point("evaluate")
        workflow.add_edge("evaluate", "generate_feedback")
        workflow.add_edge("generate_feedback", END)

        return workflow.compile()

    def evaluate(
        self,
        question: str,
        question_type: str,
        correct_answer: str,
        student_answer: str,
        attempt_count: int = 1
    ) -> Dict[str, Any]:
        """
        Public endpoint to evaluate a student's answer using the Socratic flow.
        """
        base_state = {
            "question": question,
            "question_type": question_type,
            "correct_answer": correct_answer,
            "student_answer": student_answer,
            "attempt_count": attempt_count,
            "is_correct": False,
            "feedback": "",
            "status": ""
        }
        
        result = self.workflow.invoke(base_state)
        
        return {
            "is_correct": result.get("is_correct", False),
            "feedback": result.get("feedback", ""),
            "status": result.get("status", "completed")
        }
