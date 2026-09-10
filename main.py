import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from database.tables import init_db
from backend.agents.orchestrator import OrchestratorAgent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
orchestrator = OrchestratorAgent()

# API Models
class StudentCreate(BaseModel):
    name: str

class AnswerSubmit(BaseModel):
    question_id: str
    answer: str
    attempt_count: int = 1
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
def get_next_question(student_id: str, subject: str = "Unknown"):
    try:
        result = orchestrator.get_next_question(student_id, subject)
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

# Mount frontend
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
os.makedirs(frontend_path, exist_ok=True)

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/quiz")
def serve_quiz():
    return FileResponse(os.path.join(frontend_path, "quiz.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)