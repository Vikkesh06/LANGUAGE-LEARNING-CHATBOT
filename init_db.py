import sqlite3
from werkzeug.security import generate_password_hash

def initialize_database():
    # Connect to the database (or create it)
    with sqlite3.connect('database.db') as conn:
        conn.execute('PRAGMA journal_mode=WAL;')  # Helps reduce lock issues

        # Create the users table with all necessary columns
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                security_answer TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                reset_token TEXT,
                bio TEXT,
                urls TEXT,
                profile_picture TEXT,
                dark_mode INTEGER DEFAULT 0
            )
        ''')
        print("✅ Table 'users' created/verified!")

        # Create the quiz_results table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'quiz_results' created/verified!")

        # Create the notifications table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✅ Table 'notifications' created/verified!")

        # Create admin user if not exists
        try:
            admin_password = generate_password_hash('adminpassword')
            conn.execute(
                "INSERT OR IGNORE INTO users (username, email, password, security_answer, is_admin) VALUES (?, ?, ?, ?, ?)",
                ('admin', 'kishenkish18@gmail.com', admin_password, 'admin', 1)
            )
            conn.commit()
            print("✅ Admin user created/verified!")
        except Exception as e:
            print(f"⚠ Error creating admin user: {e}")

        # Check and add any missing columns that might be needed
        try:
            conn.execute('ALTER TABLE users ADD COLUMN bio TEXT;')
            conn.commit()
            print("✅ Column 'bio' added successfully!")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            conn.execute('ALTER TABLE users ADD COLUMN urls TEXT;')
            conn.commit()
            print("✅ Column 'urls' added successfully!")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            conn.execute('ALTER TABLE users ADD COLUMN dark_mode INTEGER DEFAULT 0;')
            conn.commit()
            print("✅ Column 'dark_mode' added successfully!")
        except sqlite3.OperationalError:
            pass  # Column already exists

    print("✅ Database initialized successfully!")

if __name__ == '__main__':
    initialize_database()