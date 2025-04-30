import sqlite3
from werkzeug.security import generate_password_hash

# Connect to the database (or create it)
with sqlite3.connect('database.db') as conn:
    conn.execute('PRAGMA journal_mode=WAL;')  # Helps reduce lock issues

    # Create the users table with necessary columns
    conn.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,  -- New email column
            password TEXT NOT NULL,
            security_answer TEXT NOT NULL,  -- New column for security question answer
            is_admin INTEGER DEFAULT 0,  -- New column to identify if the user is an admin
            reset_token TEXT,  -- New column to store reset token for password reset
            bio TEXT  -- New column for bio
        )
    ''')

    # Add the 'bio' column if it doesn't exist
    try:
        conn.execute('ALTER TABLE users ADD COLUMN bio TEXT;')
        conn.commit()
        print("✅ Column 'bio' added successfully!")
    except sqlite3.OperationalError:
        print("⚠ Column 'bio' already exists.")

    # Add the 'security_answer' column if it doesn't exist
    try:
        conn.execute('ALTER TABLE users ADD COLUMN security_answer TEXT;')
        conn.commit()
        print("✅ Column 'security_answer' added successfully!")
    except sqlite3.OperationalError:
        print("⚠ Column 'security_answer' already exists.")

    conn.commit()

print("✅ Database initialized successfully!")
