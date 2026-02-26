import sqlite3

conn = sqlite3.connect("campus.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT roll, course, year, branch, section FROM students")

rows = cur.fetchall()

if not rows:
    print("❌ No students found")
else:
    print("✅ Student data:\n")
    for r in rows:
        print(dict(r))

conn.close()