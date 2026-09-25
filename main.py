import os
import sys
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

@app.get("/api/next_question/{student_id}")
def get_next_question(student_id: str, subject: str = "Unknown", topic: Optional[str] = None):
    try:
        result = orchestrator.get_next_question(student_id, subject, topic=topic)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # We need a safe fallback for topics, maybe just a default or empty list
        topics = []
        
        conn.execute("""
            INSERT INTO ingested_documents (id, filename, subject, chapters, extracted_topics, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (doc_id, file.filename, subject, chapter, json.dumps(topics), "completed"))
        conn.commit()
        conn.close()
        
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
def get_questions(subject: str = None, topic: str = None, difficulty: str = None):
    conn = get_db_connection()
    query = "SELECT * FROM generated_questions WHERE 1=1"
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
        
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    out = []
    for r in rows:
        d = dict(r)
        if isinstance(d["question_data"], str):
            try:
                qd = json.loads(d["question_data"])
                d["bloom_level"] = qd.get("bloom_level")
                d["validation_score"] = qd.get("validation_score")
                d["generation_version"] = qd.get("generation_version")
            except:
                pass
        out.append(d)
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
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/welcome")
def serve_welcome():
    return FileResponse(os.path.join(frontend_path, "welcome.html"))

@app.get("/quiz")
def serve_quiz():
    return FileResponse(os.path.join(frontend_path, "quiz.html"))

<<<<<<< HEAD
=======
@app.get("/quiz/summary")
def serve_summary():
    return FileResponse(os.path.join(frontend_path, "summary.html"))

>>>>>>> 0800c7dd2c8c5852e1d97ed7ed3ce40836820e44
@app.get("/progress")
def serve_progress():
    return FileResponse(os.path.join(frontend_path, "progress.html"))

@app.get("/library")
def serve_library():
    return FileResponse(os.path.join(frontend_path, "library.html"))

<<<<<<< HEAD
=======
@app.get("/questions")
def serve_questions():
    return FileResponse(os.path.join(frontend_path, "questions.html"))

>>>>>>> 0800c7dd2c8c5852e1d97ed7ed3ce40836820e44
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)