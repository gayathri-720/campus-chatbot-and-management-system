import sqlite3

conn = sqlite3.connect("campus.db")
cur = conn.cursor()

# Fix students table
cur.execute("""
UPDATE students
SET year = '4'
WHERE year LIKE '%4%'
""")

# Fix quizzes table
cur.execute("""
UPDATE quizzes
SET year = '4'
WHERE year LIKE '%4%'
""")

conn.commit()
conn.close()

print("✅ All year values normalized to '4'")