import sqlite3

conn = sqlite3.connect('outputs/dashboard_cache.db')
conn.row_factory = sqlite3.Row

print("Team ID | Display Name")
print("-" * 50)
for r in conn.execute("select team_id, display_name from teams").fetchall():
    print(r['team_id'], "|", r['display_name'])
