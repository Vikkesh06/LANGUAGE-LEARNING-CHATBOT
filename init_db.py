# init_db.py - Database initialization for the Language Learning Quiz Application
"""
This module initializes the SQLite database for the application.
It creates all necessary tables and sets up default data if needed.
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

def initialize_database():
    """
    Initializes the SQLite database with all required tables.
    Creates default admin user if it doesn't exist.
    """
    # Connect to the database (or create it if it doesn't exist)
    with sqlite3.connect('database.db') as conn:
        # Use Write-Ahead Logging for better concurrency and reliability
        conn.execute('PRAGMA journal_mode=WAL;')  # Helps reduce lock issues

        # --- Create Tables ---

        # Users table - stores user account information
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,         -- Username for login
                email TEXT UNIQUE NOT NULL,            -- Email address (also used for login)
                password TEXT NOT NULL,                -- Hashed password
                security_answer TEXT NOT NULL,         -- Answer to security question for account recovery
                is_admin INTEGER DEFAULT 0,            -- Admin flag (1 = admin, 0 = regular user)
                reset_token TEXT,                      -- Token for password reset
                bio TEXT,                              -- User profile bio
                urls TEXT,                             -- Social media links
                profile_picture TEXT,                  -- Profile picture filename
                dark_mode INTEGER DEFAULT 0            -- UI theme preference
            )
        ''')

        # Quiz results table - stores detailed quiz results with points tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,              -- User who took the quiz
                language TEXT NOT NULL,                -- Language of the quiz
                difficulty TEXT NOT NULL,              -- Difficulty level
                score INTEGER NOT NULL,                -- Number of correct answers
                total INTEGER NOT NULL,                -- Total number of questions
                percentage REAL NOT NULL,              -- Score percentage
                passed INTEGER DEFAULT 0,              -- Whether the quiz was passed (≥80%)
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                question_details TEXT NOT NULL,        -- JSON with detailed question data
                points_earned INTEGER DEFAULT 0,       -- Base points earned
                streak_bonus INTEGER DEFAULT 0,        -- Bonus points from streaks
                time_bonus INTEGER DEFAULT 0,          -- Bonus points from fast answers
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Badges table - tracks user achievements
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,              -- User who earned the badge
                language TEXT NOT NULL,                -- Language the badge was earned in
                badge_id TEXT NOT NULL,                -- Badge identifier
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, language, badge_id)    -- Prevent duplicate badges
            )
        ''')

        # Notifications table - stores user notifications
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,              -- User who received the notification
                message TEXT NOT NULL,                 -- Notification message
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,             -- Whether notification has been read
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # --- Create Default Admin User ---
        # Get admin credentials from environment variables or use defaults
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')

        try:
            # Create admin user with hashed password
            hashed_password = generate_password_hash(admin_password)
            conn.execute(
                "INSERT OR IGNORE INTO users (username, email, password, security_answer, is_admin) VALUES (?, ?, ?, ?, ?)",
                (admin_username, admin_email, hashed_password, 'admin', 1)
            )
        except Exception as e:
            print(f"Error creating admin user: {e}")

        # Commit all changes
        conn.commit()
        print("✅ Database initialized successfully!")

if __name__ == '__main__':
    initialize_database()