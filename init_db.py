import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database (or create it)
with sqlite3.connect('database.db') as conn:
    conn.execute('PRAGMA journal_mode=WAL;')  # Helps reduce lock issues
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

print("✅ Database initialized successfully!")