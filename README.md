# AdaptEd

An adaptive learning platform.

## Project Structure

- `backend/`: Server-side logic and API.
- `frontend/`: Client-side interface.
- `agents/`: Intelligent learning and AI agents.
- `database/`: Database schemas, migrations, and seeds.
- `tests/`: Automated unit and integration tests.
- `docs/`: Technical documentation and design resources.

## Setup Instructions

1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure your environment variables:
   ```bash
   cp .env.example .env
   ```

## Agents
- **Content Ingestion Agent**: Extracts, chunks, and stores educational materials using ChromaDB.
- **Question Generation Agent**: Generates validated educational questions based on extracted chunks using Gemini.
- **Socratic Evaluation Agent**: Evaluates student answers using a Socratic hint-first loop instead of immediately revealing the correct answer.
