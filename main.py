import os
import sys
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from database.tables import init_db
from backend.agents.orchestrator import OrchestratorAgent
from backend.agents.content_ingestion import ContentIngestionAgent
from backend.agents.question_generation import QuestionGenerationAgent
from database.connections import get_db_connection
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
orchestrator = OrchestratorAgent()
ingestion_agent = ContentIngestionAgent()
qgen_agent = QuestionGenerationAgent()

# API Models
class StudentCreate(BaseModel):
    name: str

class AnswerSubmit(BaseModel):
    question_id: str
    answer: str
    attempt_count: int = 1
    subject: str = "Unknown"

class QuestionGenerate(BaseModel):
    topic: str
    difficulty: str
    count: int = 1
    subject: str = "Unknown"

# API Endpoints
@app.post("/api/students")
def create_student(student: StudentCreate):
    student_id = orchestrator.create_student(student.name)
    return {"student_id": student_id, "name": student.name}

@app.get("/api/revision/{student_id}")
def get_revision(student_id: str, subject: str = "Unknown"):
    try:
        revision_list = orchestrator.get_todays_revision(student_id, subject)
        return {"revision": revision_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse, JSONResponse
import logging

logger = logging.getLogger(__name__)

def _sanitize_error_msg(msg: str) -> str:
    """Removes potential API keys or sensitive secrets from error messages."""
    if not msg:
        return "An internal generation error occurred."
    clean = re.sub(r'(?:AIza[0-9A-Za-z-_]{35}|nova_sk_[0-9A-Za-z-_]{20,}|sk-[0-9A-Za-z]{20,})', '[REDACTED_KEY]', str(msg))
    return clean

@app.get("/api/next_question/{student_id}")
def get_next_question(student_id: str, subject: str = "Unknown", topic: Optional[str] = None):
    try:
        result = orchestrator.get_next_question(student_id, subject, topic=topic)
        if result.get("status") == "error" or not result.get("success", True):
            err_msg = result.get("message") or "Failed to generate question"
            err_details = _sanitize_error_msg(result.get("details") or err_msg)
            logger.error(f"[Adaptive Practice] Question generation error: {err_msg} | Details: {err_details}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "status": "error",
                    "error": "Question generation failed",
                    "details": err_details,
                    "message": err_msg
                }
            )
        return result
    except Exception as e:
        logger.error(f"[Adaptive Practice] Pipeline exception for student {student_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "status": "error",
                "error": "Question generation failed",
                "details": _sanitize_error_msg(str(e)),
                "message": "Question generation failed"
            }
        )

@app.post("/api/answer/{student_id}")
def submit_answer(student_id: str, submission: AnswerSubmit):
    try:
        result = orchestrator.process_answer(
            student_id=student_id,
            question_id=submission.question_id,
            student_answer=submission.answer,
            attempt_count=submission.attempt_count
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/{student_id}")
def get_analytics(student_id: str, subject: str = "Unknown"):
    try:
        return orchestrator.get_analytics(student_id, subject)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...), subject: str = Form(...), chapter: Optional[str] = Form(None)):
    if file.size and file.size > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 25 MB.")
    
    file_bytes = await file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 25 MB.")
        
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    try:
        result = ingestion_agent.ingest(temp_path)
        
        # Save to DB
        conn = get_db_connection()
        import uuid
        import json
        doc_id = str(uuid.uuid4())
        
        # Provide meaningful extracted topics
        topics = []
        if chapter and chapter.strip():
            topics.append(chapter.strip())
        if subject and subject.strip() and subject.strip() not in topics:
            topics.append(subject.strip())
        
        conn.execute("""
            INSERT INTO ingested_documents (id, filename, subject, chapters, extracted_topics, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_id, file.filename, subject, chapter, json.dumps(topics), "completed"))
        conn.commit()
        conn.close()
        
        result["filename"] = file.filename
        result["document_id"] = doc_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/documents")
def get_documents():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, filename, subject, chapters, extracted_topics, status, created_at FROM ingested_documents").fetchall()
    conn.close()
    return {"documents": [dict(r) for r in rows]}

@app.get("/api/subjects")
def get_subjects():
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT subject FROM ingested_documents WHERE subject IS NOT NULL").fetchall()
    conn.close()
    return {"subjects": [r["subject"] for r in rows]}

@app.get("/api/questions")
def get_questions(subject: str = None, topic: str = None, difficulty: str = None, student_id: Optional[str] = None):
    """List generated questions, flattened for the question-bank UI.

    When ``student_id`` is given, each question also carries the student's
    attempt status (``correct`` / ``incorrect`` / ``unattempted``).
    """
    conn = get_db_connection()
    query = "SELECT id, subject, topic, difficulty, question_data, created_at FROM generated_questions WHERE 1=1"
    params = []
    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if topic:
        query += " AND topic = ?"
        params.append(topic)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()

    # Latest attempt per question for this student (performance_logs has one row per attempt)
    attempts = {}
    if student_id:
        log_rows = conn.execute("""
            SELECT question_id, correct, attempt_count, hint_used, timestamp
            FROM performance_logs
            WHERE student_id = ?
            ORDER BY timestamp ASC, id ASC
        """, (student_id,)).fetchall()
        for lr in log_rows:
            attempts[lr["question_id"]] = dict(lr)
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        qd = {}
        if isinstance(d.get("question_data"), str):
            try:
                qd = json.loads(d["question_data"])
            except Exception:
                qd = {}
        item = {
            "id": d["id"],
            "subject": d["subject"],
            "topic": d["topic"],
            "difficulty": d["difficulty"],
            "date": d.get("created_at"),
            "question_text": qd.get("question_text"),
            "options": qd.get("options"),
            "correct_answer": qd.get("correct_answer"),
            "explanation": qd.get("explanation"),
            "question_type": qd.get("question_type", "mcq"),
            "bloom_level": qd.get("bloom_level"),
            "source": qd.get("source_chunk_id"),
            "validation_score": qd.get("validation_score"),
            "generation_version": qd.get("generation_version"),
            "status": "unattempted",
            "user_answer": None,
        }
        attempt = attempts.get(d["id"])
        if attempt:
            item["status"] = "correct" if attempt["correct"] else "incorrect"
            item["attempt_count"] = attempt["attempt_count"]
            item["hint_used"] = bool(attempt["hint_used"])
        out.append(item)
    return {"questions": out}

@app.post("/api/questions/generate")
def generate_questions(req: QuestionGenerate):
    try:
        result = qgen_agent.generate_questions(req.topic, req.count, req.difficulty)
        
        # Save to DB
        conn = get_db_connection()
        subject = req.subject
        for q in result.get("questions", []):
            import uuid
            q_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO generated_questions (id, subject, topic, difficulty, question_data)
                VALUES (?, ?, ?, ?, ?)
            """, (q_id, subject, req.topic, req.difficulty, json.dumps(q.dict())))
        conn.commit()
        conn.close()
        
        return {"status": "success", "generated_count": len(result.get("questions", []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule/{student_id}")
def get_schedule(student_id: str):
    conn = get_db_connection()
    rows = conn.execute("SELECT topic, next_review_date, interval FROM spaced_repetition WHERE student_id = ?", (student_id,)).fetchall()
    conn.close()
    return {"schedule": [dict(r) for r in rows]}

# Mount frontend
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
os.makedirs(frontend_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_path, "landing.html"))

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/welcome")
def serve_welcome():
    return FileResponse(os.path.join(frontend_path, "welcome.html"))

@app.get("/quiz")
def serve_quiz():
    return FileResponse(os.path.join(frontend_path, "quiz.html"))

@app.get("/quiz/summary")
def serve_summary():
    return FileResponse(os.path.join(frontend_path, "summary.html"))
@app.get("/progress")
def serve_progress():
    return FileResponse(os.path.join(frontend_path, "progress.html"))

@app.get("/library")
def serve_library():
    return FileResponse(os.path.join(frontend_path, "library.html"))

@app.get("/questions")
def serve_questions():
    return FileResponse(os.path.join(frontend_path, "questions.html"))
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)