import sqlite3
from pathlib import Path

db_path = Path("outputs/dashboard_cache.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT issue_type FROM tickets_current")
    types = cursor.fetchall()
    print("Distinct issue types in database:")
    for t in types:
        print(f"- {t[0]!r}")
    conn.close()
