import sqlite3

conn = sqlite3.connect("campus.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM quizzes")

rows = cur.fetchall()

if not rows:
    print("❌ No quiz data in database")
else:
    print("✅ Quiz data found:\n")
    for r in rows:
        print(dict(r))

conn.close()