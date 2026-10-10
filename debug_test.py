import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from backend.agents.orchestrator import OrchestratorAgent
from database.connections import get_db_connection

def main():
    conn = get_db_connection()
    docs = conn.execute("SELECT * FROM ingested_documents").fetchall()
    print("Ingested documents in DB:", len(docs))

    students = conn.execute("SELECT * FROM students").fetchall()
    print("Students in DB:", [s["id"] for s in students])

    if students:
        s_id = students[0]["id"]
        orc = OrchestratorAgent()
        print("Testing get_next_question for student:", s_id)
        try:
            res = orc.get_next_question(s_id, "Unknown")
            print("Result:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

