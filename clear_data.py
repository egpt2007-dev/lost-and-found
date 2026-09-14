import sqlite3

conn = sqlite3.connect("lost_and_found.db")
conn.execute("DELETE FROM claims")
conn.execute("DELETE FROM items")
conn.commit()
conn.close()
print("All test data cleared.")