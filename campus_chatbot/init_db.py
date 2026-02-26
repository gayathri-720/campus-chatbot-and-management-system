import sqlite3
import os

# ================= DATABASE PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "campus.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ================= USERS (LOGIN) =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # ================= STUDENTS =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll TEXT PRIMARY KEY,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            fees_status TEXT DEFAULT 'NOT PAID'
        )
    """)

    # ================= ATTENDANCE =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (roll) REFERENCES students (roll)
        )
    """)

    # ================= STUDY MATERIALS (CLASS-WISE) =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            filename TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            uploaded_by TEXT,
            upload_date TEXT NOT NULL
        )
    """)

    # ================= QUIZ =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            question TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_option INTEGER NOT NULL
        )
    """)

    # ================= INTERNAL MARKS =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS internal_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            branch TEXT NOT NULL,
            section TEXT NOT NULL,
            mid TEXT NOT NULL,
            bit INTEGER DEFAULT 0,
            assignment INTEGER DEFAULT 0,
            theory INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            FOREIGN KEY (roll) REFERENCES students (roll)
        )
    """)

    conn.commit()
    conn.close()

    print("✅ Database & all tables created successfully!")

# ================= RUN =================
if __name__ == "__main__":
    init_db()