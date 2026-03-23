import sqlite3
import os

db_path = os.path.join("backend", "spinning_photon.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in {db_path}: {[t['name'] for t in tables]}")

job_id = "9158ef7e"
if "jobs" in [t['name'] for t in tables]:
    cursor.execute("SELECT id, topic, video_type, workflow_mode FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()

    if row:
        print(f"ID: {row['id']}")
        print(f"Topic: {row['topic']}")
        print(f"Video Type: {row['video_type']}")
        print(f"Workflow Mode: {row['workflow_mode']}")
    else:
        print(f"Job {job_id} not found.")
else:
    print("Table 'jobs' not found.")

conn.close()
