import json
import os
from typing import TypedDict, Dict, Any

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from backend.services.llm import get_chat_model

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
        self._llm = None  # created lazily on first use (see backend/services/llm.py)
        self.workflow = self._build_workflow()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = self._get_llm()
        return self._llm

    @llm.setter
    def llm(self, value):
        self._llm = value

    def _get_llm(self):
        # Provider (Nova API / Gemini) and model come from .env; see backend/services/llm.py
        return get_chat_model(temperature=0.3)

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
                from backend.services.llm import extract_json
                parsed_result = extract_json(raw_text)
                return {"is_correct": bool(parsed_result.get("is_correct", False))}
            except Exception as e:
                try:
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                    parsed_result = json.loads(clean_json)
                    return {"is_correct": bool(parsed_result.get("is_correct", False))}
                except Exception:
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
            try:
                response = self.llm.invoke(explanation_prompt)
                raw_text = extract_text(response.content)
                feedback_text = raw_text.strip()
            except Exception:
                feedback_text = f"The correct answer is: {state.get('correct_answer')}."
            return {"feedback": feedback_text, "status": "completed"}
        
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
            try:
                response = self.llm.invoke(hint_prompt)
                raw_text = extract_text(response.content)
                feedback_text = raw_text.strip()
            except Exception:
                feedback_text = "Not quite. Think carefully about the key requirements and constraints of this concept, and consider which option satisfies all criteria."
            return {"feedback": feedback_text, "status": "retry"}

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
