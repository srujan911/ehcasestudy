import sqlite3

conn = sqlite3.connect("results.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS submissions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    password TEXT,
    ts INTEGER
)
""")
conn.commit()
conn.close()

print("Database created!")
