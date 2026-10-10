import os
import sys
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.connections import get_db_connection
from database.tables import init_db

if __name__ == "__main__":
    init_db()
    conn = get_db_connection()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables in DB:", tables)

    students = [dict(r) for r in conn.execute("SELECT * FROM students").fetchall()]
    print("Students count:", len(students))
    if students:
        print("First student:", students[0])

    mastery = [dict(r) for r in conn.execute("SELECT * FROM topic_mastery").fetchall()]
    print("Topic mastery count:", len(mastery))

    questions = [dict(r) for r in conn.execute("SELECT * FROM generated_questions").fetchall()]
    print("Generated questions count:", len(questions))

    conn.close()

