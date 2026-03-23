"""One-time script to update player image_url from .png to .webp in the database."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'auction.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM player WHERE image_url LIKE '%.png'")
count = cur.fetchone()[0]
print(f"Players with .png URLs: {count}")

cur.execute("UPDATE player SET image_url = REPLACE(image_url, '.png', '.webp') WHERE image_url LIKE '%.png'")
print(f"Updated: {cur.rowcount} rows")

conn.commit()
conn.close()
print("Done.")
