from .connections import get_db_connection

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Topic Mastery table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_mastery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            mastery_level REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            UNIQUE(student_id, subject, topic)
        )
    """)
    
    # Spaced Repetition table (SM-2 simplified)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spaced_repetition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            interval REAL DEFAULT 1.0,
            repetition INTEGER DEFAULT 0,
            easiness REAL DEFAULT 2.5,
            next_review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            UNIQUE(student_id, subject, topic)
        )
    """)
    
    # Performance Logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            correct BOOLEAN NOT NULL,
            attempt_count INTEGER DEFAULT 1,
            hint_used BOOLEAN DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)
    
    # Cache for generated questions to avoid regenerating same ones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_questions (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
