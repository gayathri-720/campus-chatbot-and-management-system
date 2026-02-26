import sqlite3

conn = sqlite3.connect("campus.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM internal_marks")

rows = cur.fetchall()

if not rows:
    print("❌ No internal marks found in table")
else:
    print("✅ Internal marks found:\n")
    for r in rows:
        print(dict(r))

conn.close()