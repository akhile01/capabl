# 🎓 AdaptEd - AI-Powered Adaptive Learning Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114.0%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4.svg)](https://deepmind.google/technologies/gemini/)
[![LangChain](https://img.shields.io/badge/Framework-LangChain-🦜🔗.svg)](https://www.langchain.com/)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-FF6F00.svg)](https://www.trychroma.com/)

**AdaptEd** is an intelligent, agent-driven adaptive learning platform built to personalize educational experiences. By leveraging Retrieval-Augmented Generation (RAG), self-critiquing AI agents, Socratic feedback loops, and spaced repetition, AdaptEd automatically turns raw educational documents (such as textbook PDFs) into targeted practice questions, dynamic hints, and mastery-based revision workflows.

---

## 🏗️ Architecture & Core Agents

AdaptEd is built around a modular multi-agent orchestration system:

```
                  ┌───────────────────────────────┐
                  │      Educational Document     │
                  │         (PDF Upload)          │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │    Content Ingestion Agent      │
                 │ (PyPDF + Chunking + Metadata)  │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │       Chroma Vector Store       │
                 │      (Semantic Search Index)    │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │  Question Generation Agent      │
                 │  (RAG + Gemini + Self-Critique) │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
 ┌────────────────────────────────┴────────────────────────────────┐
 │                     Master Orchestrator                         │
 │        (Adaptive Scheduling + SM-2 Spaced Repetition)          │
 └───────────────┬─────────────────────────────────┬───────────────┘
                 │                                 │
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │ Socratic Evaluation Agent │     │     FastAPI & Web UI      │
   │  (Hint-First Pedagogy)    │     │   (Interactive Student)   │
   └───────────────────────────┘     └───────────────────────────┘
```

### 🤖 Agent Breakdown

1. **Content Ingestion Agent** ([backend/agents/content_ingestion.py](file:///c:/Users/TEJA%20SWAROOP/Desktop/capable%20D/capable-orchetration/backend/agents/content_ingestion.py))
   - Extracts text from PDF files using `PyPDFLoader`.
   - Tags content with metadata (subject, chapter, topic).
   - Dynamically chunks text using `RecursiveCharacterTextSplitter`.
   - Embeds and persists text vectors in ChromaDB for high-precision retrieval.

2. **Question Generation Agent** ([backend/agents/question_generation.py](file:///c:/Users/TEJA%20SWAROOP/Desktop/capable%20D/capable-orchetration/backend/agents/question_generation.py))
   - Performs RAG retrieval from ChromaDB based on target topic and difficulty.
   - Generates Multiple Choice Questions (MCQs) aligned with Bloom's Taxonomy.
   - Implements a **Self-Critique & Validation Loop** checking for groundedness, factual correctness, clear distractors, and accurate answer indices before final approval.
   - Prevents duplicate question generation by inspecting historical question logs.

3. **Socratic Evaluation Agent** ([backend/agents/socratic_agent.py](file:///c:/Users/TEJA%20SWAROOP/Desktop/capable%20D/capable-orchetration/backend/agents/socratic_agent.py))
   - Evaluates student quiz answers using pedagogical best practices.
   - Rather than immediately revealing answers on wrong attempts, it delivers **Socratic hints** to encourage critical thinking and deeper understanding.

4. **Master Orchestrator Agent** ([backend/agents/orchestrator.py](file:///c:/Users/TEJA%20SWAROOP/Desktop/capable%20D/capable-orchetration/backend/agents/orchestrator.py))
   - Tracks individual student mastery levels per topic.
   - Schedules topic reviews using an adaptive Spaced Repetition algorithm (SM-2 variant).
   - Serves as the central bridge between database records, cached question stores, and front-facing API routes.

---

## ✨ Features

- 📄 **Automated PDF Processing**: Ingest course units and textbooks into structured vector embeddings.
- 🎯 **Adaptive Questioning**: Automatically tailors difficulty (`easy`, `medium`, `hard`) according to student topic mastery.
- 🧠 **Socratic Learning Loop**: Provides progressive hints on incorrect answers instead of static answer keys.
- 🔄 **Spaced Repetition Engine**: Calculates optimal review intervals so students revise topics right before forgetting them.
- 📊 **Performance Analytics**: Tracks topic accuracy, total attempts, mastery level progression, and revision schedules.
- 🌐 **Interactive Web UI**: Modern, responsive dark-themed web interface for student onboarding, quiz taking, and analytics visualization.

---

## 📁 Repository Structure

```
capable-orchetration/
├── agents/                      # Specialized agent definitions
├── backend/
│   ├── agents/                  # Core AI agents (Ingestion, Generation, Socratic, Orchestrator)
│   ├── database/                # SQLite connection managers & schema tables
│   ├── model/                   # Pydantic data models (Question, Student, Performance)
│   ├── prompts/                 # LLM System Prompts & validation criteria
│   └── services/                # Document loaders, text chunkers, embeddings & vector store
├── data/
│   └── uploads/                 # Sample PDFs for ingestion (e.g. UNIT-5.pdf)
├── database/                    # Root database helpers & initializers
├── docs/                        # Project documentation and specifications
├── frontend/                    # Web Interface
│   ├── index.html               # Student onboarding & dashboard
│   ├── quiz.html                # Interactive adaptive quiz view
│   ├── style.css                # CSS styling tokens & layout rules
│   └── app.js                   # Frontend state management & API interaction
├── tests/                       # Pytest test suite
│   ├── test_content_ingestion.py
│   ├── test_models.py
│   ├── test_orchestrator.py
│   ├── test_question_generation.py
│   └── test_socratic_agent.py
├── .env.example                 # Environment variable template
├── main.py                      # FastAPI Web Server entry point
├── requirements.txt             # Python project dependencies
├── run_e2e.py                   # Live End-to-End ingestion & generation pipeline script
├── run_ingestion.py             # Standalone PDF ingestion script
└── run_mock.py                  # Mocked E2E pipeline (works without API keys)
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

- Python 3.10 or higher
- Git

### 2. Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/akhile01/capabl.git
   cd capabl
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Or using Windows launcher: `py -m pip install -r requirements.txt`)*

3. Set up environment variables:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Update `.env` with your Google Gemini API key:
   ```ini
   GEMINI_API_KEY=your_gemini_api_key_here
   DATABASE_URL=sqlite:///database.db
   PORT=8000
   HOST=0.0.0.0
   DEBUG=True
   ```

---

## 🏃 Running the Project

### Option A: Launch the Web Application (Recommended)

Start the FastAPI web server to access the full interactive interface:

```bash
py main.py
```
Open your browser and navigate to:
- **Student Dashboard**: `http://localhost:8000/`
- **Adaptive Quiz Engine**: `http://localhost:8000/quiz`

---

### Option B: Run Mocked Pipeline (No API Key Required)

Test the internal multi-agent flow with simulated LLM responses:

```bash
py run_mock.py
```

---

### Option C: Run Live E2E Pipeline (Requires Gemini API Key)

Ingest real PDFs, generate RAG-grounded questions via Gemini, and simulate Socratic evaluation:

```bash
# 1. Ingest PDF into Chroma Vector Database
py run_ingestion.py

# 2. Run complete end-to-end flow
py run_e2e.py
```

---

### Option D: Run Automated Tests

Execute the comprehensive unit and integration test suite:

```bash
py -m pytest
```

---

## 📡 API Reference

The FastAPI server (`main.py`) exposes the following endpoints:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/students` | Create a new student profile |
| `GET` | `/api/revision/{student_id}` | Retrieve today's due & weak revision topics |
| `GET` | `/api/next_question/{student_id}` | Fetch or generate the next adaptive question |
| `POST` | `/api/answer/{student_id}` | Submit an answer & get Socratic hint/feedback |
| `GET` | `/api/analytics/{student_id}` | Get topic mastery metrics and performance logs |

---

## 🛡️ License

This project is licensed under the MIT License.
