# add_campaign_col.py
import sqlite3, os, sys

DB = "results.db"
if not os.path.exists(DB):
    print("results.db not found in", os.getcwd()); sys.exit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# check if column exists
cur.execute("PRAGMA table_info(submissions);")
cols = [r[1] for r in cur.fetchall()]
print("Columns before:", cols)

if "campaign" in cols:
    print("campaign column already exists.")
else:
    cur.execute("ALTER TABLE submissions ADD COLUMN campaign TEXT;")
    conn.commit()
    print("Added campaign column.")

cur.execute("PRAGMA table_info(submissions);")
print("Columns after:", [r[1] for r in cur.fetchall()])

conn.close()
