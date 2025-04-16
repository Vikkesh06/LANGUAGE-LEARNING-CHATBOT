from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(_name_)
app.secret_key = 'supersecretkey'  # Needed for session handling

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_login(username, password):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", 
            (username,)
        ).fetchone()
    
    if user and check_password_hash(user['password'], password):
        return user
    return None

def register_user(username, password):
    with get_db_connection() as conn:
        # Check if username already exists
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user:
            return False

    # If username doesn't exist, proceed with registration
    try:
        hashed_password = generate_password_hash(password)  # Hash the password
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = check_login(username, password)
        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Invalid username or password."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        success = register_user(username, password)
        if success:
            return redirect(url_for('login'))
        else:
            error = "⚠ Username already exists."
    return render_template('register.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- New Routes for Chatbot, Progress, and Settings ---
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'username' in session:
        return render_template('chatbot.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/progress')
def progress():
    if 'username' in session:
        return render_template('progress.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' in session:
        if request.method == 'POST':
            new_password = request.form['new_password']
            hashed_password = generate_password_hash(new_password)
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, session['username']))
                conn.commit()
            return redirect(url_for('dashboard'))
        return render_template('settings.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    if 'dark_mode' in session:
        session.pop('dark_mode')
    else:
        session['dark_mode'] = True
    return redirect(url_for('dashboard'))

if _name_ == '_main_':
    app.run(debug=True)