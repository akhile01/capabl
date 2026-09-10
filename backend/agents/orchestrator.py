import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
import random

from database.connections import get_db_connection
from backend.agents.question_generation import QuestionGenerationAgent
from backend.agents.socratic_agent import SocraticEvaluationAgent
from backend.model.question import Question

class OrchestratorAgent:
    def __init__(self):
        self.question_agent = QuestionGenerationAgent()
        self.socratic_agent = SocraticEvaluationAgent()

    def _get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        conn.close()
        return dict(student) if student else None

    def create_student(self, name: str) -> str:
        student_id = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute("INSERT INTO students (id, name) VALUES (?, ?)", (student_id, name))
        conn.commit()
        conn.close()
        return student_id

    def get_todays_revision(self, student_id: str, subject: str = "Unknown") -> List[Dict[str, Any]]:
        conn = get_db_connection()
        
        # 1. Due topics
        now = datetime.datetime.now()
        due_rows = conn.execute("""
            SELECT topic, mastery_level FROM topic_mastery
            WHERE student_id = ? AND subject = ?
            AND topic IN (
                SELECT topic FROM spaced_repetition
                WHERE student_id = ? AND subject = ? AND next_review_date <= ?
            )
        """, (student_id, subject, student_id, subject, now)).fetchall()
        
        # 2. Weak topics (mastery < 0.6)
        weak_rows = conn.execute("""
            SELECT topic, mastery_level FROM topic_mastery
            WHERE student_id = ? AND subject = ? AND mastery_level < 0.6
        """, (student_id, subject)).fetchall()
        
        conn.close()
        
        due_topics = [dict(row) for row in due_rows]
        weak_topics = [dict(row) for row in weak_rows]
        
        # Combine and prioritize
        combined = {}
        for t in due_topics + weak_topics:
            topic_name = t["topic"]
            if topic_name not in combined:
                combined[topic_name] = {
                    "topic": topic_name,
                    "mastery_level": t["mastery_level"],
                    "is_due": any(d["topic"] == topic_name for d in due_topics),
                    "is_weak": any(w["topic"] == topic_name for w in weak_topics)
                }
        
        # Sort by due status first, then by weakness
        revision_list = sorted(
            list(combined.values()),
            key=lambda x: (not x["is_due"], x["mastery_level"])
        )
        
        # If empty (new student), maybe pull some default topics from DB or generate some
        # We will assume frontend handles empty list or orchestrator fetches available topics if none are tracked.
        
        return revision_list

    def get_next_question(self, student_id: str, subject: str = "Unknown") -> Dict[str, Any]:
        """
        Determines the next topic and fetches/generates a question.
        Priority:
        1. Due topics.
        2. Weak topics.
        3. Random available topic.
        """
        revision_list = self.get_todays_revision(student_id, subject)
        
        # Select topic
        if revision_list:
            selected_topic = revision_list[0]["topic"]
            mastery = revision_list[0]["mastery_level"]
        else:
            # Fallback for new student
            selected_topic = "Database systems" # In real app, we fetch from available content
            mastery = 0.0
            
        # Determine difficulty based on mastery
        if mastery < 0.4:
            difficulty = "easy"
        elif mastery < 0.8:
            difficulty = "medium"
        else:
            difficulty = "hard"
            
        # Generate or fetch from cache
        conn = get_db_connection()
        cached = conn.execute("""
            SELECT id, question_data FROM generated_questions
            WHERE subject = ? AND topic = ? AND difficulty = ?
            AND id NOT IN (
                SELECT question_id FROM performance_logs WHERE student_id = ?
            )
            ORDER BY RANDOM() LIMIT 1
        """, (subject, selected_topic, difficulty, student_id)).fetchone()
        
        if cached:
            question_dict = json.loads(cached["question_data"])
            q_id = cached["id"]
            question_dict["id"] = q_id
        else:
            # Fetch ALL previously generated questions for this topic to avoid regenerating them
            prior_rows = conn.execute("""
                SELECT question_data FROM generated_questions 
                WHERE subject = ? AND topic = ?
            """, (subject, selected_topic)).fetchall()
            
            prior_qs = []
            for r in prior_rows:
                try:
                    qd = json.loads(r["question_data"])
                    prior_qs.append({"question": qd["question_text"], "correct_answer": qd["correct_answer"]})
                except:
                    pass

            # Generate new
            result = self.question_agent.generate_questions(selected_topic, 1, difficulty, prior_questions=prior_qs)
            if result.get("questions"):
                q = result["questions"][0]
                q_id = str(uuid.uuid4())
                q.id = q_id
                q.subject = subject
                question_dict = q.dict()
                
                # Cache it
                conn.execute("""
                    INSERT INTO generated_questions (id, subject, topic, difficulty, question_data)
                    VALUES (?, ?, ?, ?, ?)
                """, (q_id, subject, selected_topic, difficulty, json.dumps(question_dict)))
                conn.commit()
            else:
                conn.close()
                return {"status": "error", "message": "Failed to generate question"}
                
        conn.close()
        
        # Ensure 'id' is in the returned dictionary
        question_dict["id"] = q_id

        return {
            "status": "success",
            "question": question_dict,
            "reason": f"Selected {selected_topic} ({difficulty}) due to mastery={mastery:.2f}."
        }

    def process_answer(self, student_id: str, question_id: str, student_answer: str, attempt_count: int = 1) -> Dict[str, Any]:
        """
        Process the answer, call Socratic agent, and update mastery/SR if complete.
        """
        conn = get_db_connection()
        q_row = conn.execute("SELECT * FROM generated_questions WHERE id = ?", (question_id,)).fetchone()
        
        if not q_row:
            conn.close()
            return {"status": "error", "message": "Question not found"}
            
        q_data = json.loads(q_row["question_data"])
        question_text = q_data["question_text"]
        correct_answer = q_data["correct_answer"]
        topic = q_row["topic"]
        subject = q_row["subject"]
        difficulty = q_row["difficulty"]
        
        eval_result = self.socratic_agent.evaluate(
            question=question_text,
            question_type=q_data.get("question_type", "mcq"),
            correct_answer=correct_answer,
            student_answer=student_answer,
            attempt_count=attempt_count
        )
        
        is_correct = eval_result.get("is_correct", False)
        status = eval_result.get("status", "completed")
        hint_used = status == "retry"
        
        # Log performance
        conn.execute("""
            INSERT INTO performance_logs (student_id, question_id, subject, topic, difficulty, correct, attempt_count, hint_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, question_id, subject, topic, difficulty, is_correct, attempt_count, hint_used))
        
        # If attempt is completed (either correct, or max attempts reached)
        if status == "completed":
            self._update_mastery(conn, student_id, subject, topic, is_correct, difficulty)
            self._update_spaced_repetition(conn, student_id, subject, topic, is_correct)
            
        conn.commit()
        conn.close()
        
        return {
            "is_correct": is_correct,
            "feedback": eval_result.get("feedback", ""),
            "status": status,
            "explanation": q_data.get("explanation") if status == "completed" else None
        }

    def _update_mastery(self, conn, student_id: str, subject: str, topic: str, is_correct: bool, difficulty: str):
        row = conn.execute("SELECT mastery_level FROM topic_mastery WHERE student_id = ? AND subject = ? AND topic = ?", 
                           (student_id, subject, topic)).fetchone()
        
        current_mastery = row["mastery_level"] if row else 0.0
        
        # Adjust weight based on difficulty
        weight = 0.1
        if difficulty == "medium": weight = 0.15
        elif difficulty == "hard": weight = 0.2
        
        if is_correct:
            new_mastery = min(1.0, current_mastery + weight)
        else:
            new_mastery = max(0.0, current_mastery - (weight * 0.5))
            
        if row:
            conn.execute("UPDATE topic_mastery SET mastery_level = ?, updated_at = CURRENT_TIMESTAMP WHERE student_id = ? AND subject = ? AND topic = ?",
                         (new_mastery, student_id, subject, topic))
        else:
            conn.execute("INSERT INTO topic_mastery (student_id, subject, topic, mastery_level) VALUES (?, ?, ?, ?)",
                         (student_id, subject, topic, new_mastery))

    def _update_spaced_repetition(self, conn, student_id: str, subject: str, topic: str, is_correct: bool):
        row = conn.execute("SELECT * FROM spaced_repetition WHERE student_id = ? AND subject = ? AND topic = ?",
                           (student_id, subject, topic)).fetchone()
        
        # SM-2 inspired logic
        if not row:
            interval = 1.0 if is_correct else 0.5
            repetition = 1 if is_correct else 0
            easiness = 2.6 if is_correct else 2.0
            
            next_date = datetime.datetime.now() + datetime.timedelta(days=interval)
            conn.execute("""
                INSERT INTO spaced_repetition (student_id, subject, topic, interval, repetition, easiness, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (student_id, subject, topic, interval, repetition, easiness, next_date))
        else:
            interval = row["interval"]
            repetition = row["repetition"]
            easiness = row["easiness"]
            
            quality = 4 if is_correct else 0
            
            # Update easiness factor
            easiness = max(1.3, easiness + 0.1 - (5.0 - quality) * (0.08 + (5.0 - quality) * 0.02))
            
            if quality < 3:
                repetition = 0
                interval = 1.0
            else:
                repetition += 1
                if repetition == 1:
                    interval = 1.0
                elif repetition == 2:
                    interval = 6.0
                else:
                    interval = interval * easiness
                    
            next_date = datetime.datetime.now() + datetime.timedelta(days=interval)
            
            conn.execute("""
                UPDATE spaced_repetition 
                SET interval = ?, repetition = ?, easiness = ?, next_review_date = ?
                WHERE student_id = ? AND subject = ? AND topic = ?
            """, (interval, repetition, easiness, next_date, student_id, subject, topic))

    def get_analytics(self, student_id: str, subject: str = "Unknown"):
        conn = get_db_connection()
        mastery = conn.execute("SELECT topic, mastery_level FROM topic_mastery WHERE student_id = ? AND subject = ?", (student_id, subject)).fetchall()
        logs = conn.execute("SELECT topic, correct, difficulty, hint_used, timestamp FROM performance_logs WHERE student_id = ? AND subject = ? ORDER BY timestamp DESC LIMIT 50", (student_id, subject)).fetchall()
        conn.close()
        return {
            "mastery": [dict(m) for m in mastery],
            "recent_performance": [dict(l) for l in logs]
        }
