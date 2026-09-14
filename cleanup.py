import sqlite3

conn = sqlite3.connect("lost_and_found.db")
conn.execute("DELETE FROM items WHERE description = ?", ("Black bag found near the library entrance",))
conn.commit()
conn.close()
print("cleaned up")