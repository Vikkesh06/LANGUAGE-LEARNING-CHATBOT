from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from werkzeug.utils import secure_filename
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from random import sample

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session handling

# --- File Upload Setup ---
UPLOAD_FOLDER = 'static/uploads/'  # Folder where profile pictures will be saved
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- SMTP Configuration ---
smtp_server = "smtp.gmail.com"
smtp_port = 465  # For SSL connection
smtp_user = "kishenkish18@gmail.com"
smtp_password = 'pxcu tasw ndev hnvf'

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_user_id(email):
    with get_db_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            return user['id']
    return None

def check_login(email, password, security_answer):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",  
            (email,)
        ).fetchone()
    
    if user and check_password_hash(user['password'], password) and user['security_answer'] == security_answer:
        return user
    return None

def register_user(username, email, password, security_answer):
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            return False

    try:
        hashed_password = generate_password_hash(password)  
        with get_db_connection() as conn:
            conn.execute("INSERT INTO users (username, email, password, security_answer) VALUES (?, ?, ?, ?)", 
                         (username, email, hashed_password, security_answer))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# --- OTP Functions ---
def generate_otp():
    return str(random.randint(100000, 999999))  # 6-digit OTP

def send_otp(email, otp):
    try:
        print(f"\n=== Attempting to send OTP to {email} ===")
        
        msg = MIMEMultipart()
        msg['From'] = "kishenkish18@gmail.com"
        msg['To'] = email
        msg['Subject'] = "Your Login OTP Code"
        
        body = f"""
        Your OTP verification code is: {otp}
        This code will expire in 10 minutes.
        """
        msg.attach(MIMEText(body, 'plain'))

        print("Connecting to SMTP server...")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        print("SMTP connection established")
        
        print("Logging in to SMTP server...")
        server.login(smtp_user, smtp_password)
        print("SMTP login successful")
        
        print("Sending email...")
        server.sendmail("kishenkish18@gmail.com", email, msg.as_string())
        print("Email sent successfully!")
        
        server.quit()
        print("SMTP connection closed")
        
        flash(f"OTP sent to {email}. Check your inbox (and spam folder).", 'info')
        return True
        
    except Exception as e:
        print(f"\n!!! Error sending OTP: {str(e)} !!!")
        flash('Error sending OTP. Please try again or contact support.', 'error')
        return False

# --- Notification Function ---
def add_notification(user_id, notification_message):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, message, timestamp) VALUES (?, ?, ?)",
            (user_id, notification_message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

# Quiz questions data structure
QUIZ_DATA = {
    "English": {
        "beginner": [
            {"question": "What is the English word for 'libro'?", "options": ["Book", "Door", "Window", "Chair"], "answer": "Book"},
            {"question": "How do you say 'hello' in English?", "options": ["Hola", "Hello", "Bonjour", "Ciao"], "answer": "Hello"},
            {"question": "What is the opposite of 'hot'?", "options": ["Cold", "Warm", "Spicy", "Sweet"], "answer": "Cold"}
        ],
        "intermediate": [
            {"question": "Which sentence is correct?", "options": ["She go to school", "She goes to school", "She going to school", "She gone to school"], "answer": "She goes to school"},
            {"question": "What is the past tense of 'run'?", "options": ["Runned", "Ran", "Running", "Runs"], "answer": "Ran"}
        ],
        "advanced": [
            {"question": "What does 'bite the bullet' mean?", "options": ["To eat something hard", "To endure a painful situation", "To chew loudly", "To avoid a problem"], "answer": "To endure a painful situation"},
            {"question": "Which is a synonym for 'gregarious'?", "options": ["Shy", "Sociable", "Angry", "Quiet"], "answer": "Sociable"}
        ]
    },
    "Spanish": {
        "beginner": [
            {"question": "How do you say 'hello' in Spanish?", "options": ["Hola", "Adiós", "Gracias", "Por favor"], "answer": "Hola"},
            {"question": "What does 'gracias' mean?", "options": ["Hello", "Goodbye", "Thank you", "Please"], "answer": "Thank you"}
        ],
        "intermediate": [
            {"question": "How do you say 'I am hungry' in Spanish?", "options": ["Tengo frío", "Tengo hambre", "Tengo sed", "Tengo sueño"], "answer": "Tengo hambre"}
        ]
    }
    # Add more languages as needed
}

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("\n--- Login route accessed ---")
    
    if 'username' in session and session.get('verified'):
        print("Already logged in, redirecting to dashboard")
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        print("POST request received")
        email = request.form.get('email')
        password = request.form.get('password')
        security_answer = request.form.get('security_answer')
        
        print(f"Form data - Email: {email}, Security Answer: {security_answer}")
        
        if not all([email, password, security_answer]):
            error = "All fields are required"
            flash(error, 'error')
            print("Missing fields error")
            return redirect(url_for('login'))
        
        user = check_login(email, password, security_answer)
        
        if user:
            print("User authenticated successfully")
            print(f"User details - ID: {user['id']}, Username: {user['username']}")
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = email
            session['verified'] = False
            
            # Record login time
            session['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            otp = generate_otp()
            session['otp'] = otp
            print(f"Generated OTP: {otp}")
            
            send_otp(email, otp)
            print("OTP sent, redirecting to verify_otp")
            return redirect(url_for('verify_otp'))
        else:
            error = "Invalid email, password, or security answer"
            flash(error, 'error')
            print("Authentication failed")
            return redirect(url_for('login'))
    
    print("Rendering login page")
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    error = None
    if request.method == 'POST':
        otp_entered = request.form['otp']
        if otp_entered == session.get('otp'):
            session['verified'] = True
            # Add login notification
            add_notification(session['user_id'], "You logged in successfully")
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Invalid OTP."
    return render_template('verify_otp.html', error=error)

@app.route('/resend_otp', methods=['GET'])
def resend_otp():
    if 'email' in session:
        otp = generate_otp()
        session['otp'] = otp
        send_otp(session['email'], otp)
        flash("✅ A new OTP has been sent to your email.")
    return redirect(url_for('verify_otp'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                reset_token = secrets.token_urlsafe(16)
                with get_db_connection() as conn:
                    conn.execute("UPDATE users SET reset_token = ? WHERE email = ?", (reset_token, email))
                    conn.commit()

                msg = MIMEMultipart()
                msg['From'] = "kishenkish18@gmail.com"
                msg['To'] = email
                msg['Subject'] = 'Password Reset Request'
                body = f"Click here to reset your password: http://localhost:5000/reset_password/{reset_token}"
                msg.attach(MIMEText(body, 'plain'))

                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                server.login(smtp_user, smtp_password)
                server.sendmail("kishenkish18@gmail.com", email, msg.as_string())
                server.quit()

                flash('Check your email for the password reset link.')
                return redirect(url_for('login'))
            else:
                error = "⚠ Email not found in our records."
    return render_template('forgot_password.html', error=error)

@app.route('/reset_password/<reset_token>', methods=['GET', 'POST'])
def reset_password(reset_token):
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)
        with get_db_connection() as conn:
            conn.execute("UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?", 
                         (hashed_password, reset_token))
            conn.commit()
        flash("Your password has been successfully updated.")
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        security_answer = request.form['security_answer']
        success = register_user(username, email, password, security_answer)
        if success:
            return redirect(url_for('login'))
        else:
            error = "⚠ Email already exists."
    return render_template('register.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session or not session.get('verified'):
        return redirect(url_for('login'))
    
    # Get notification count
    with get_db_connection() as conn:
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
            (session['user_id'],)
        ).fetchone()[0]
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         notification_count=notification_count)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Admin Routes ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'kishenkish18@gmail.com' and password == 'adminpassword':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "❌ Invalid email or password for admin."
    return render_template('admin_login.html', error=error)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' in session:
        with get_db_connection() as conn:
            users = conn.execute("SELECT * FROM users").fetchall()
        return render_template('admin_dashboard.html', users=users)
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'admin' in session:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'username' in session:
        if request.method == 'POST':
            user_message = request.form['user_message']
            bot_response = handle_chatbot_response(user_message)
            return jsonify({'bot_response': bot_response})
        return render_template('chatbot.html', username=session['username'])
    return redirect(url_for('login'))

def handle_chatbot_response(user_message):
    if user_message.lower() in ["hello", "hi", "hey"]:
        return "Hello! How can I help you with your language learning today?"
    elif user_message.lower() == "grammar tip":
        return "In Spanish, adjectives usually come after the noun."
    else:
        return "I'm here to help with vocabulary and grammar tips. Ask me anything!"

@app.route('/progress')
def progress():
    if 'username' in session:
        return render_template('progress.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (session['username'],)).fetchone()
    conn.close()

    if request.method == 'POST':
        email = request.form.get('email')
        bio = request.form.get('bio')
        new_password = request.form.get('new_password')
        urls = request.form.get('urls')
        
        profile_pic_filename = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_pic_filename = filename

        try:
            conn = get_db_connection()
            update_data = {
                'email': email,
                'bio': bio,
                'urls': urls
            }
            
            if new_password:
                update_data['password'] = generate_password_hash(new_password)
            
            if profile_pic_filename:
                update_data['profile_picture'] = profile_pic_filename
            
            set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values())
            values.append(session['username'])
            
            conn.execute(
                f"UPDATE users SET {set_clause} WHERE username = ?",
                values
            )
            conn.commit()
            conn.close()
            
            if profile_pic_filename:
                session['profile_picture'] = profile_pic_filename
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('settings'))
            
        except Exception as e:
            conn.close()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('settings.html', 
                         username=session['username'],
                         user=user)

@app.route('/notifications')
def notifications():
    if 'username' in session:
        user_id = session['user_id']
        with get_db_connection() as conn:
            notifications = conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,)
            ).fetchall()
        return render_template('notifications.html', notifications=notifications)
    return redirect(url_for('login'))

@app.route('/notifications/count')
def notifications_count():
    if 'username' not in session:
        return jsonify({'count': 0})
    
    with get_db_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
            (session['user_id'],)
        ).fetchone()[0]
    
    return jsonify({'count': count})

@app.route('/notifications/json')
def notifications_json():
    if 'username' not in session:
        return jsonify([])
    
    user_id = session['user_id']
    with get_db_connection() as conn:
        notifications = conn.execute(
            "SELECT message, timestamp FROM notifications WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        ).fetchall()
    
    notifications_list = [{
        'message': notification['message'],
        'timestamp': notification['timestamp']
    } for notification in notifications]
    
    return jsonify(notifications_list)

@app.route('/quiz')
def quiz():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    languages = ['English', 'Chinese', 'Malay', 'Spanish', 'French', 'Portuguese', 'Tamil']
    return render_template('quiz.html', languages=languages)

@app.route('/quiz/<difficulty>')
def quiz_level(difficulty):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    language = request.args.get('language', 'English')
    raw_questions = QUIZ_DATA.get(language, {}).get(difficulty, [])
    
    if not raw_questions:
        flash(f"No {difficulty} questions available for {language} yet", 'info')
        return redirect(url_for('quiz'))
    
    # Prepare questions with proper structure
    questions = []
    for i, q in enumerate(raw_questions, 1):
        questions.append({
            'number': i,          # Unique question number
            'text': q['question'], # Question text
            'options': q['options'], # Answer choices
            'answer': q['answer']  # Correct answer
        })
    
    return render_template('quiz_questions.html',
                         questions=questions,
                         difficulty=difficulty,
                         language=language)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    language = request.form.get('language')
    difficulty = request.form.get('difficulty')
    form_data = request.form
    
    # Get original questions for checking answers
    original_questions = QUIZ_DATA.get(language, {}).get(difficulty, [])
    score = 0
    results = []
    
    # Check each answer
    for i, question in enumerate(original_questions, 1):
        user_answer = form_data.get(f'q_{i}')
        is_correct = user_answer == question['answer']
        
        if is_correct:
            score += 1
            
        results.append({
            'question': question['question'],
            'user_answer': user_answer,
            'correct_answer': question['answer'],
            'is_correct': is_correct
        })
    
    # Save results to database
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO quiz_results (user_id, language, difficulty, score, total) VALUES (?, ?, ?, ?, ?)",
            (session['user_id'], language, difficulty, score, len(original_questions))
        )
        conn.commit()
        
        # Add notification about quiz completion
        add_notification(session['user_id'], 
                        f"You scored {score}/{len(original_questions)} in {language} {difficulty} quiz")
    except Exception as e:
        print(f"Error saving quiz results: {e}")
        flash("Error saving your quiz results", 'error')
    finally:
        conn.close()
    
    return render_template('quiz_results.html',
                         score=score,
                         total=len(original_questions),
                         results=results,
                         language=language,
                         difficulty=difficulty)

@app.route('/get_quiz_progress/<int:user_id>')
def get_quiz_progress(user_id):
    if 'username' not in session:
        return jsonify([])
    
    with get_db_connection() as conn:
        # Get the most recent attempt for each language
        quiz_results = conn.execute('''
            SELECT r1.language, r1.score, r1.total 
            FROM quiz_results r1
            INNER JOIN (
                SELECT language, MAX(timestamp) as latest_timestamp
                FROM quiz_results
                WHERE user_id = ?
                GROUP BY language
            ) r2 ON r1.language = r2.language AND r1.timestamp = r2.latest_timestamp
            WHERE r1.user_id = ?
        ''', (user_id, user_id)).fetchall()
    
    progress_data = [dict(row) for row in quiz_results]
    return jsonify(progress_data)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Create tables if they don't exist
    with get_db_connection() as conn:
        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                security_answer TEXT NOT NULL,
                reset_token TEXT,
                profile_picture TEXT,
                bio TEXT,
                urls TEXT
            )
        ''')
        
        # Quiz results table
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
        
        # Notifications table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
    
    app.run(debug=True)