from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
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
import traceback  # Import traceback for detailed error logging
import csv
import difflib  # For similarity ratio
import mimetypes
import pandas as pd  # Add this import at the top

app = Flask(__name__)
CORS(app)
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

# Replace with your actual API key from Google AI Studio
API_KEY = "AIzaSyC0M-x3-IiWaroDCwHo59vcF4GBWijhPC0"  # <-- Replace this with your key from Google AI Studio

genai.configure(api_key=API_KEY)

# Use the latest model version
model = genai.GenerativeModel('gemini-2.0-flash')  # Using the more stable and widely available model

# Add Gemini Vision model for image support
vision_model = genai.GenerativeModel('gemini-pro-vision')

# Dictionary to store quiz data from CSVs
CSV_QUIZ_DATA = {}

# Add these constants near the top of your file (after imports, before routes)
LEVEL_REQUIREMENTS = {
    'beginner': {'points': 100},
    'intermediate': {'points': 250},
    'advanced': {'points': 500},
    'fluent': {'points': 1000}
}
POINTS_PER_CORRECT_ANSWER = 10
STREAK_BONUS = 15

# Map language to Excel file
QUIZ_EXCEL_MAP = {
    'English': 'data/english_quiz_questions.xlsx',
    'Malay': 'data/malay_quiz_questions.xlsx',
    'Chinese': 'data/chinese_quiz_questions.xlsx',
    'Tamil': 'data/tamil_quiz_questions.xlsx',
    'Portuguese': 'data/portuguese_quiz_questions.xlsx',
    'Spanish': 'data/spanish_quiz_questions.xlsx',
    'French': 'data/french_quiz_questions.xlsx',
}

# Helper to load questions from Excel

def load_quiz_questions_from_excel(language, difficulty):
    file_path = QUIZ_EXCEL_MAP.get(language)
    if not file_path or not os.path.exists(file_path):
        return []
    df = pd.read_excel(file_path)
    # Expect columns: Question, Options, Answer, Difficulty (case-insensitive)
    # Normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    # Filter by difficulty
    filtered = df[df['difficulty'].str.lower() == difficulty.lower()]
    questions = []
    for _, row in filtered.iterrows():
        options = row['options']
        if isinstance(options, str):
            options = [opt.strip() for opt in options.split(';')]
        else:
            options = []
        questions.append({
            'question': row['question'],
            'options': options,
            'answer': row['answer']
        })
    return questions

def load_quiz_data_from_csv(filepath, language):
    """
    Loads quiz data from a CSV file.
    Assumes CSV format: Question,Options,Correct Answer
    Options are semicolon-separated.
    """
    quiz_list = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            next(reader) # Skip header row
            for row in reader:
                if len(row) == 3:
                    question = row[0].strip()
                    options = [opt.strip() for opt in row[1].split(';')]
                    answer = row[2].strip()
                    quiz_list.append({'question': question, 'options': options, 'answer': answer})
                else:
                    print(f"Skipping invalid row in {filepath}: {row}")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {filepath}")
    except Exception as e:
        print(f"Error loading quiz data from {filepath}: {e}")
    return quiz_list

# --- Helper Functions ---

def get_gemini_response(prompt):
    """
    Sends a prompt to the Gemini API and returns the response.
    Handles errors robustly.
    """
    try:
        # Create a new model instance for each request
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Set up the generation config
        generation_config = {
            "temperature": 0.7,
            "top_p": 1,
            "top_k": 32,
            "max_output_tokens": 800,
        }

        # Set up safety settings
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]

        # Generate the response
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        # Check if we got a valid response
        if response and hasattr(response, 'text'):
            return response.text.strip()
        else:
            print("Empty or invalid response from Gemini API")
            return "I apologize, but I couldn't generate a proper response. Please try again."

    except Exception as e:
        print(f"Error in get_gemini_response: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return "I apologize, but there was an error processing your request. Please try again."

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
            "INSERT INTO notifications (user_id, message, timestamp, is_read) VALUES (?, ?, ?, 0)",
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
    
    # Get unread notification count
    with get_db_connection() as conn:
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
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
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get notification count
    with get_db_connection() as conn:
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (session['user_id'],)
        ).fetchone()[0]
    
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message', '')
        language = data.get('language', 'english')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Include relevant quiz data if available for this language
        quiz_data = CSV_QUIZ_DATA.get(language, [])
        if quiz_data:
            # Select a few random questions to include in the prompt
            sample_size = min(5, len(quiz_data)) # Include up to 5 questions
            sample_questions = random.sample(quiz_data, sample_size)
            message += "\n\nHere are some practice questions you can refer to:\n"
            for i, q in enumerate(sample_questions):
                options_str = '; '.join(q['options'])
                message += f"Q{i+1}: {q['question']} Options: {options_str} Answer: {q['answer']}\n"

        prompt = f"""You are a helpful and encouraging language tutor teaching {language}. 
        The student's message is: "{message}"
        
        Please provide a very concise response that directly addresses the student's message. Avoid unnecessary details or conversational filler unless specifically asked.
        
        Provide your response in the following format:
        1. First, respond concisely in {language}, focusing on directly addressing the student's message.
        2. Then, on a new line, provide the English translation of your response.
        
        Format your response exactly like this:
        [Response in {language}]
        [English translation]
        
        Response:"""

        response_text = get_gemini_response(prompt)
        
        # Split the response into the target language response and English translation
        response_parts = response_text.split('\n', 1)
        target_language_response = response_parts[0].strip()
        english_translation = response_parts[1].strip() if len(response_parts) > 1 else ""
        
        # Store the message and response
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO chat_messages (session_id, message, bot_response)
                VALUES (?, ?, ?)
            ''', (session_id, message, response_text))
            conn.commit()

        return jsonify({
            'response': target_language_response,
            'translation': english_translation,
            'session_id': session_id
        }), 200

    return render_template('chatbot.html', 
                         username=session['username'],
                         notification_count=notification_count)

@app.route('/progress')
def progress():
    if 'username' not in session:
        return redirect(url_for('login'))

    # MOCK DATA: Replace with real DB logic as needed
    user_progress = {
        'progress': {
            'English': {
                'icon': 'flag-usa',
                'current_level': 'beginner',
                'total_points': 80,
                'quizzes_taken': 3,
                'streak': 2,
                'highest_streak': 3,
                'next_level': True,
                'levels': {
                    'beginner': {'points_earned': 80},
                    'intermediate': {'points_earned': 0},
                    'advanced': {'points_earned': 0},
                    'fluent': {'points_earned': 0},
                },
                'badges': ['basic_vocab'],
            },
            'Spanish': {
                'icon': 'flag-spain',
                'current_level': 'intermediate',
                'total_points': 180,
                'quizzes_taken': 5,
                'streak': 1,
                'highest_streak': 2,
                'next_level': True,
                'levels': {
                    'beginner': {'points_earned': 100},
                    'intermediate': {'points_earned': 80},
                    'advanced': {'points_earned': 0},
                    'fluent': {'points_earned': 0},
                },
                'badges': ['basic_vocab', 'simple_sentences'],
            },
        },
        'total_quizzes': 8,
        'recent_activity': [
            {
                'language': 'English',
                'score': 7,
                'total': 10,
                'difficulty': 'beginner',
                'timestamp': '2024-06-01 10:00',
                'streak_bonus': 0,
                'time_bonus': 5,
                'points_earned': 75,
                'passed': True,
            },
            {
                'language': 'Spanish',
                'score': 8,
                'total': 10,
                'difficulty': 'intermediate',
                'timestamp': '2024-06-02 12:00',
                'streak_bonus': 10,
                'time_bonus': 0,
                'points_earned': 90,
                'passed': True,
            },
        ],
        'LEVEL_REQUIREMENTS': LEVEL_REQUIREMENTS,
        'POINTS_PER_CORRECT_ANSWER': POINTS_PER_CORRECT_ANSWER,
        'STREAK_BONUS': STREAK_BONUS,
    }

    return render_template('progress.html', progress=user_progress, username=session['username'])

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (session['username'],)).fetchone()
    avatars = []
    avatars_dir = os.path.join('static', 'avatars')
    if os.path.exists(avatars_dir):
        avatars = [f for f in os.listdir(avatars_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if request.method == 'POST':
        action = request.form.get('action', 'save_profile')
        if action == 'save_profile':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            location = request.form.get('location')
            website = request.form.get('website')
            bio = request.form.get('bio')
            urls = []
            for key, values in request.form.lists():
                if key == 'urls':
                    for value in values:
                        if value and value.strip():
                            urls.append(value.strip())
            urls_str = '\n'.join(urls) if urls else ''
            profile_pic_filename = request.form.get('profile_picture') or None
            selected_avatar = request.form.get('selected_avatar')
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_pic_filename = filename
            try:
                update_data = {}
                if name is not None:
                    update_data['name'] = name
                if email is not None:
                    update_data['email'] = email
                if phone is not None:
                    update_data['phone'] = phone
                if location is not None:
                    update_data['location'] = location
                if website is not None:
                    update_data['website'] = website
                if bio is not None:
                    update_data['bio'] = bio
                update_data['urls'] = urls_str
                if selected_avatar:
                    update_data['avatar'] = selected_avatar
                    update_data['profile_picture'] = None
                elif profile_pic_filename:
                    update_data['profile_picture'] = profile_pic_filename
                    update_data['avatar'] = None
                if update_data:
                    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                    values = list(update_data.values())
                    values.append(session['username'])
                    with get_db_connection() as conn:
                        conn.execute(
                            f"UPDATE users SET {set_clause} WHERE username = ?",
                            values
                        )
                        conn.commit()
                    flash('Profile updated successfully!', 'success')
                return redirect(url_for('settings'))
            except Exception as e:
                flash(f'Error updating profile: {str(e)}', 'error')
        elif action == 'change_password':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            if not new_password:
                flash('Please enter a new password', 'error')
                return redirect(url_for('settings'))
            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('settings'))
            try:
                hashed_password = generate_password_hash(new_password)
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (hashed_password, session['username'])
                    )
                    conn.commit()
                flash('Password updated successfully!', 'success')
                return redirect(url_for('settings'))
            except Exception as e:
                flash(f'Error updating password: {str(e)}', 'error')
        elif action == 'save_preferences':
            timezone = request.form.get('timezone')
            datetime_format = request.form.get('datetime_format')
            try:
                update_data = {}
                if timezone:
                    update_data['timezone'] = timezone
                if datetime_format:
                    update_data['datetime_format'] = datetime_format
                if update_data:
                    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                    values = list(update_data.values())
                    values.append(session['username'])
                    with get_db_connection() as conn:
                        conn.execute(
                            f"UPDATE users SET {set_clause} WHERE username = ?",
                            values
                        )
                        conn.commit()
                flash('Preferences updated successfully!', 'success')
                return redirect(url_for('settings'))
            except Exception as e:
                flash(f'Error updating preferences: {str(e)}', 'error')
    return render_template('settings.html',
                         username=session['username'],
                         user=user,
                         avatars=avatars)

@app.route('/notifications')
def notifications():
    if 'username' in session:
        user_id = session['user_id']
        with get_db_connection() as conn:
            # Get unread notifications
            unread_notifications = conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY timestamp DESC",
                (user_id,)
            ).fetchall()
            
            # Get read notifications
            read_notifications = conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? AND is_read = 1 ORDER BY timestamp DESC",
                (user_id,)
            ).fetchall()
            
        return render_template('notifications.html', 
                            unread_notifications=unread_notifications,
                            read_notifications=read_notifications)
    return redirect(url_for('login'))

@app.route('/notifications/count')
def notifications_count():
    if 'username' not in session:
        return jsonify({'count': 0})
    
    with get_db_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
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
            "SELECT id, message, timestamp, is_read FROM notifications WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        ).fetchall()
    
    notifications_list = [{
        'id': notification['id'],
        'message': notification['message'],
        'timestamp': notification['timestamp'],
        'is_read': bool(notification['is_read'])
    } for notification in notifications]
    
    return jsonify(notifications_list)

@app.route('/mark_notification_read', methods=['POST'])
def mark_notification_read():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403

    data = request.get_json()
    notification_id = data.get('notification_id')

    if not notification_id:
        return jsonify({'status': 'error', 'message': 'Missing notification_id'}), 400

    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?', 
                (notification_id, session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/mark_all_notifications_read', methods=['POST'])
def mark_all_notifications_read():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403

    user_id = session['user_id']
    conn = get_db_connection()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/quiz')
def quiz():
    if 'username' not in session:
        return redirect(url_for('login'))
    languages = ['English', 'Malay', 'Chinese', 'Tamil', 'Portuguese', 'Spanish', 'French']
    return render_template('quiz.html', languages=languages)

@app.route('/quiz/<difficulty>')
def quiz_level(difficulty):
    if 'username' not in session:
        return redirect(url_for('login'))
    language = request.args.get('language', 'English')
    allowed_languages = ['English', 'Malay', 'Chinese', 'Tamil', 'Portuguese', 'Spanish', 'French']
    if language not in allowed_languages:
        flash('Invalid language selected.', 'danger')
        return redirect(url_for('quiz'))
    questions = load_quiz_questions_from_excel(language, difficulty)
    if not questions:
        flash(f"No {difficulty} questions available for {language} yet", 'info')
        return redirect(url_for('quiz'))
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

@app.route('/chat_history/sessions')
def get_chat_sessions():
    if 'username' not in session:
        return jsonify([])
    
    with get_db_connection() as conn:
        sessions = conn.execute('''
            SELECT cs.session_id, cs.language, cs.started_at, cs.last_message_at,
                   (SELECT message FROM chat_messages WHERE session_id = cs.session_id ORDER BY timestamp ASC LIMIT 1) as first_message
            FROM chat_sessions cs
            WHERE cs.user_id = ?
            ORDER BY cs.last_message_at DESC
        ''', (session['user_id'],)).fetchall()
    
    return jsonify([dict(session) for session in sessions])

@app.route('/chat_history/session/<session_id>')
def get_session_messages(session_id):
    if 'username' not in session:
        return jsonify([])
    
    with get_db_connection() as conn:
        # Verify the session belongs to the user
        session_owner = conn.execute(
            'SELECT user_id FROM chat_sessions WHERE session_id = ?',
            (session_id,)
        ).fetchone()
        
        if not session_owner or session_owner['user_id'] != session['user_id']:
            return jsonify([])
        
        messages = conn.execute('''
            SELECT message, bot_response, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,)).fetchall()
    
    return jsonify([dict(message) for message in messages])

@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({'error': 'Please log in to use the chatbot'}), 401
    try:
        # Accept both JSON and multipart/form-data
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            print("Received multipart/form-data")
            print("Files received:", request.files)
            print("Form data received:", request.form)
            message = request.form.get('message', '').strip()
            language = request.form.get('language', 'english').strip()
            session_id = request.form.get('session_id')
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data received'}), 400
            message = data.get('message', '').strip()
            language = data.get('language', 'english').strip()
            session_id = data.get('session_id')
            image_file = None
        if not message and not image_file:
            return jsonify({'error': 'Message or image is required'}), 400
        # Create or update chat session
        with get_db_connection() as conn:
            if session_id:
                conn.execute('''
                    UPDATE chat_sessions 
                    SET last_message_at = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND user_id = ?
                ''', (session_id, session['user_id']))
            else:
                session_id = f"sess-{secrets.token_hex(16)}"
                conn.execute('''
                    INSERT INTO chat_sessions (session_id, user_id, language)
                    VALUES (?, ?, ?)
                ''', (session_id, session['user_id'], language))
        # If image is present, use Gemini Vision
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                image_file.save(file_path)
                print(f"Image saved to {file_path}")
                file_size = os.path.getsize(file_path)
                print(f"Image file size: {file_size} bytes")
            except Exception as e:
                print(f"Error saving image: {e}")
                return jsonify({'error': 'Failed to save the uploaded image.'}), 500

            # Try Gemini Vision first (if you want to keep it as a fallback, otherwise comment this block)
            gemini_failed = False
            prompt = f"""
You are a helpful and encouraging language tutor. The user has uploaded an image and asked: '{message}'.

1. First, carefully analyze the image and provide a detailed description of what is shown, including any objects, people, text, or context. If possible, include interesting facts or cultural notes about what you see.
2. Then, translate your description into {language} in a clear and natural way, as if explaining to a language learner.
3. Finally, provide the English translation of your {language} response on a new line.

Format your response exactly like this:
[Response in {language}]
[English translation]

Response:
"""
            print("Gemini Vision Prompt:\n", prompt)
            try:
                with open(file_path, 'rb') as img_f:
                    image_bytes = img_f.read()
                print(f"Read {len(image_bytes)} bytes from image file.")
                try:
                    response = vision_model.generate_content([prompt, image_bytes])
                    if response and hasattr(response, 'text') and response.text.strip():
                        response_text = response.text.strip()
                    else:
                        print("Empty or invalid response from Gemini Vision API (bytes method)")
                        gemini_failed = True
                except Exception as e_bytes:
                    print(f"Gemini Vision API error with bytes: {e_bytes}")
                    gemini_failed = True
            except Exception as e:
                print(f"Error in Gemini Vision image processing: {str(e)}")
                print(f"Full traceback: {traceback.format_exc()}")
                gemini_failed = True

            # If Gemini Vision failed, use BLIP
            if gemini_failed:
                print("Falling back to BLIP image captioning...")
                try:
                    from PIL import Image
                    from transformers import BlipProcessor, BlipForConditionalGeneration
                    import torch
                    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
                    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
                    raw_image = Image.open(file_path).convert('RGB')
                    inputs = processor(raw_image, return_tensors="pt")
                    out = model.generate(**inputs)
                    caption = processor.decode(out[0], skip_special_tokens=True)
                    print(f"BLIP caption: {caption}")
                    # Now translate the caption using Gemini text model
                    translation_prompt = f"Translate the following image description into {language}, then provide the English translation on a new line.\nDescription: {caption}\n\nFormat:\n[Response in {language}]\n[English translation]\n\nResponse:"
                    response_text = get_gemini_response(translation_prompt)
                except Exception as blip_e:
                    print(f"BLIP image captioning error: {blip_e}")
                    response_text = 'Sorry, there was an error analyzing the image (BLIP). Please ensure all dependencies are installed.'
        else:
            # Text-only fallback
            prompt_text = f"You are a helpful and encouraging language tutor teaching {language}. The student's message is: '{message}'\nPlease provide a very concise response that directly addresses the student's message. Avoid unnecessary details or conversational filler unless specifically asked.\nProvide your response in the following format:\n[Response in {language}]\n[English translation]\nResponse:"
            response_text = get_gemini_response(prompt_text)
        # Split the response into the target language response and English translation
        response_parts = response_text.split('\n', 1)
        target_language_response = response_parts[0].strip()
        english_translation = response_parts[1].strip() if len(response_parts) > 1 else ""
        # Store the message and response
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO chat_messages (session_id, message, bot_response)
                VALUES (?, ?, ?)
            ''', (session_id, message, response_text))
            conn.commit()
        return jsonify({
            'response': target_language_response,
            'translation': english_translation,
            'session_id': session_id
        }), 200
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'An error occurred processing your message'}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Function to ensure database has required columns ---
def ensure_user_columns():
    columns = [
        ('name', 'TEXT'),
        ('phone', 'TEXT'),
        ('location', 'TEXT'),
        ('website', 'TEXT'),
        ('avatar', 'TEXT'),
        ('timezone', 'TEXT'),
        ('datetime_format', 'TEXT'),
        ('is_active', 'INTEGER DEFAULT 1')
    ]
    with get_db_connection() as conn:
        for col, typ in columns:
            try:
                conn.execute(f'ALTER TABLE users ADD COLUMN {col} {typ};')
            except Exception:
                pass  # Already exists
        conn.commit()

# Call this at startup
ensure_user_columns()

@app.route('/deactivate_account', methods=['POST'])
def deactivate_account():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (session['user_id'],)
            )
            conn.commit()
            add_notification(
                session['user_id'],
                "Your account has been deactivated. You can reactivate it at any time."
            )
            flash('Your account has been deactivated. You have been logged out.', 'info')
            session.clear()
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Error deactivating account: {str(e)}', 'error')
        return redirect(url_for('settings'))

@app.route('/reactivate_account', methods=['GET', 'POST'])
def reactivate_account():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        security_answer = request.form.get('security_answer')
        reason = request.form.get('reason')
        if not all([email, password, security_answer, reason]):
            flash('All fields are required', 'error')
            return redirect(url_for('reactivate_account'))
        try:
            with get_db_connection() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE email = ? AND is_active = 0",
                    (email,)
                ).fetchone()
                if not user:
                    flash('No deactivated account found with this email', 'error')
                    return redirect(url_for('reactivate_account'))
                if not (check_password_hash(user['password'], password) and user['security_answer'] == security_answer):
                    flash('Invalid credentials', 'error')
                    return redirect(url_for('reactivate_account'))
                conn.execute(
                    "UPDATE users SET is_active = 1 WHERE email = ?",
                    (email,)
                )
                conn.commit()
                add_notification(
                    user['id'],
                    "Your account has been reactivated. Welcome back!"
                )
                conn.execute(
                    "INSERT INTO account_activity (user_id, activity_type, details) VALUES (?, ?, ?)",
                    (user['id'], 'reactivation', reason)
                )
                conn.commit()
                flash('Your account has been reactivated successfully!', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error reactivating account: {str(e)}', 'error')
            return redirect(url_for('reactivate_account'))
    return render_template('reactivate_account.html')

@app.route('/close_account', methods=['POST'])
def close_account():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user_id = session['user_id']
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Please provide a reason for closing your account', 'error')
        return redirect(url_for('settings'))
    try:
        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            conn.execute('''
                INSERT INTO account_activity (user_id, activity_type, details)
                VALUES (?, 'account_closure', ?)
            ''', (user_id, reason))
            session_ids = [row['session_id'] for row in 
                          conn.execute("SELECT session_id FROM chat_sessions WHERE user_id = ?", 
                                      (user_id,)).fetchall()]
            for session_id in session_ids:
                conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM quiz_results_enhanced WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.execute("COMMIT")
            flash('Your account has been permanently deleted. You may register a new account.', 'info')
            session.clear()
            return redirect(url_for('register'))
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("ROLLBACK")
        print(f"Error closing account: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error closing account: {str(e)}', 'error')
        return redirect(url_for('settings'))

# --- Study List Endpoints ---
@app.route('/study_list')
def get_study_list():
    if 'user_id' not in session:
        return jsonify([])
    with get_db_connection() as conn:
        rows = conn.execute('SELECT word, added_at, note FROM study_list WHERE user_id = ? ORDER BY added_at DESC', (session['user_id'],)).fetchall()
    # Always return note, even if None
    return jsonify([{'word': row['word'], 'added_at': row['added_at'], 'note': row['note'] if row['note'] is not None else ''} for row in rows])

@app.route('/add_to_study_list', methods=['POST'])
def add_to_study_list():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403
    data = request.get_json()
    word = data.get('word', '').strip()
    if not word:
        return jsonify({'status': 'error', 'message': 'No word provided'}), 400
    try:
        with get_db_connection() as conn:
            # Use INSERT OR IGNORE to prevent duplicates
            conn.execute('INSERT OR IGNORE INTO study_list (user_id, word, added_at, note) VALUES (?, ?, CURRENT_TIMESTAMP, NULL)', (session['user_id'], word))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in add_to_study_list: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/save_study_note', methods=['POST'])
def save_study_note():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403
    data = request.get_json()
    word = data.get('word', '').strip()
    note = data.get('note', '').strip()
    if not word:
        return jsonify({'status': 'error', 'message': 'No word provided'}), 400
    with get_db_connection() as conn:
        conn.execute('UPDATE study_list SET note = ? WHERE user_id = ? AND word = ?', (note, session['user_id'], word))
        conn.commit()
    return jsonify({'status': 'success'})

@app.route('/get_progress_stats')
def get_progress_stats():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        with get_db_connection() as conn:
            # Get or create progress record
            progress = conn.execute(
                'SELECT * FROM user_progress WHERE user_id = ?',
                (session['user_id'],)
            ).fetchone()

            if not progress:
                # Initialize progress for new users
                conn.execute(
                    'INSERT INTO user_progress (user_id) VALUES (?)',
                    (session['user_id'],)
                )
                conn.commit()
                progress = conn.execute(
                    'SELECT * FROM user_progress WHERE user_id = ?',
                    (session['user_id'],)
                ).fetchone()

            # Update daily streak
            today = datetime.now().date()
            last_activity = datetime.strptime(progress['last_activity_date'], '%Y-%m-%d').date() if progress['last_activity_date'] else None
            
            if last_activity:
                days_diff = (today - last_activity).days
                if days_diff == 1:  # Consecutive day
                    new_streak = progress['daily_streak'] + 1
                elif days_diff == 0:  # Same day
                    new_streak = progress['daily_streak']
                else:  # Streak broken
                    new_streak = 1
            else:
                new_streak = 1

            # Calculate additional stats
            words_learned = conn.execute(
                'SELECT COUNT(*) as count FROM study_list WHERE user_id = ?',
                (session['user_id'],)
            ).fetchone()['count']

            conversation_count = conn.execute(
                'SELECT COUNT(DISTINCT session_id) as count FROM chat_sessions WHERE user_id = ?',
                (session['user_id'],)
            ).fetchone()['count']

            # Calculate accuracy rate from quiz results
            quiz_stats = conn.execute('''
                SELECT 
                    SUM(score) as total_score,
                    SUM(total) as total_questions
                FROM quiz_results 
                WHERE user_id = ?
            ''', (session['user_id'],)).fetchone()

            accuracy_rate = 0
            if quiz_stats['total_questions'] and quiz_stats['total_questions'] > 0:
                accuracy_rate = (quiz_stats['total_score'] / quiz_stats['total_questions']) * 100

            # Calculate overall progress percentage (weighted average)
            progress_percentage = min(100, (
                (words_learned * 0.4) +  # 40% weight for words learned
                (conversation_count * 0.3) +  # 30% weight for conversations
                (accuracy_rate * 0.3)  # 30% weight for accuracy
            ))

            # Check for new achievements
            achievements = []
            if words_learned >= 10 and not conn.execute(
                'SELECT 1 FROM achievements WHERE user_id = ? AND achievement_type = ?',
                (session['user_id'], 'words_10')
            ).fetchone():
                achievements.append({
                    'type': 'words_10',
                    'name': 'Word Collector',
                    'description': 'Learned 10 words'
                })
                conn.execute(
                    'INSERT INTO achievements (user_id, achievement_type, achievement_name, description) VALUES (?, ?, ?, ?)',
                    (session['user_id'], 'words_10', 'Word Collector', 'Learned 10 words')
                )

            if new_streak >= 7 and not conn.execute(
                'SELECT 1 FROM achievements WHERE user_id = ? AND achievement_type = ?',
                (session['user_id'], 'streak_7')
            ).fetchone():
                achievements.append({
                    'type': 'streak_7',
                    'name': 'Consistent Learner',
                    'description': '7-day learning streak'
                })
                conn.execute(
                    'INSERT INTO achievements (user_id, achievement_type, achievement_name, description) VALUES (?, ?, ?, ?)',
                    (session['user_id'], 'streak_7', 'Consistent Learner', '7-day learning streak')
                )

            # Update progress record
            conn.execute('''
                UPDATE user_progress 
                SET words_learned = ?,
                    conversation_count = ?,
                    accuracy_rate = ?,
         daily_streak = ?,
                    last_activity_date = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (words_learned, conversation_count, accuracy_rate, new_streak, today, session['user_id']))
            conn.commit()

            # Get all achievements
            user_achievements = conn.execute('''
                SELECT achievement_name, description, earned_at
                FROM achievements
                WHERE user_id = ?
                ORDER BY earned_at DESC
            ''', (session['user_id'],)).fetchall()

            return jsonify({
                'words_learned': words_learned,
                'conversation_count': conversation_count,
                'accuracy_rate': round(accuracy_rate, 1),
                'progress_percentage': round(progress_percentage, 1),
                'daily_streak': new_streak,
                'new_achievements': achievements,
                'achievements': [dict(achievement) for achievement in user_achievements]
            })

    except Exception as e:
        print(f"Error getting progress stats: {e}")
        return jsonify({'error': 'Error calculating progress'}), 500

@app.route('/check_pronunciation', methods=['POST'])
def check_pronunciation():
    data = request.get_json()
    expected = data.get('expected', '').strip()
    spoken = data.get('spoken', '').strip()
    language = data.get('language', 'english')
    if not expected or not spoken:
        return jsonify({'similarity': 0, 'feedback': 'Missing input.'}), 400
    # Compute similarity (case-insensitive, ignore punctuation)
    def normalize(s):
        import re
        return re.sub(r'[^\w\s]', '', s).lower()
    expected_norm = normalize(expected)
    spoken_norm = normalize(spoken)
    similarity = difflib.SequenceMatcher(None, expected_norm, spoken_norm).ratio()
    similarity_pct = int(round(similarity * 100))
    # Feedback message
    if similarity_pct > 90:
        feedback = '✅ Excellent! Your pronunciation is very close.'
    elif similarity_pct > 75:
        feedback = '👍 Good! Minor differences detected.'
    elif similarity_pct > 50:
        feedback = '🙂 Not bad, but try again for better accuracy.'
    else:
        feedback = '❌ Quite different. Listen and try to match the phrase.'
    return jsonify({'similarity': similarity_pct, 'feedback': feedback})

@app.route('/flashcards')
def flashcards():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('flashcards.html', username=session['username'])

@app.route('/get_flashcards/<language>')
def get_flashcards(language):
    # Map language to CSV file
    csv_map = {
        'english': 'static/english_multiple_choice.csv',
        'spanish': 'static/spanish_multiple_choice.csv',
        'french': 'static/french_multiple_choice.csv',
        'chinese': 'static/chinese_multiple_choice.csv',
        'tamil': 'static/tamil_multiple_choice.csv',
        'malay': 'static/malay_multiple_choice.csv',
        'portuguese': 'static/portuguese_multiple_choice.csv',
    }
    path = csv_map.get(language.lower())
    if not path:
        return jsonify([])
    flashcards = []
    try:
        with open(path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Some CSVs may have extra columns, so only use the first three
                question = row.get('Question') or list(row.values())[0]
                options = row.get('Options') or list(row.values())[1]
                answer = row.get('Correct Answer') or list(row.values())[2]
                flashcards.append({
                    'question': question,
                    'options': [opt.strip() for opt in options.split(';')] if options else [],
                    'answer': answer
                })
    except Exception as e:
        print(f'Error reading flashcards for {language}:', e)
    return jsonify(flashcards)

# --- BLIP Image Captioning Route (required for chatbox attach button) ---
from flask import request, jsonify, session

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/blip_caption', methods=['POST'])
def blip_caption():
    if 'username' not in session:
        return jsonify({'error': 'Please log in to use image captioning'}), 401
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    image_file = request.files['image']
    try:
        from PIL import Image
        from transformers import BlipProcessor, BlipForConditionalGeneration
        import torch
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        raw_image = Image.open(image_file).convert('RGB')
        inputs = processor(raw_image, return_tensors="pt")
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        return jsonify({'caption': caption})
    except Exception as e:
        print(f"BLIP image captioning error: {e}")
        return jsonify({'error': 'BLIP image captioning failed. Please ensure all dependencies are installed.'}), 500

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Load quiz data from CSV files
    csv_files = {
        'English': 'static/english_multiple_choice.csv',
        'Spanish': 'static/spanish_multiple_choice.csv',
        'French': 'static/french_multiple_choice.csv',
        'Chinese': 'static/chinese_multiple_choice.csv',
        'Malay': 'static/malay_multiple_choice.csv',
        'Portuguese': 'static/portuguese_multiple_choice.csv',
        'Tamil': 'static/tamil_multiple_choice.csv',
    }
    for lang, path in csv_files.items():
        CSV_QUIZ_DATA[lang] = load_quiz_data_from_csv(path, lang)
        print(f"Loaded {len(CSV_QUIZ_DATA[lang])} {lang} quiz questions from {path}")

    # Initialize database with all required tables
    print("\n=== Initializing Database ===")
    with get_db_connection() as conn:
        # Use Write-Ahead Logging for better concurrency and reliability
        conn.execute('PRAGMA journal_mode=WAL;')
        print("✅ WAL mode enabled!")

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
                dark_mode INTEGER DEFAULT 0,           -- UI theme preference
                name TEXT,                             -- Full name
                phone TEXT,                            -- Phone number
                location TEXT,                         -- Location/address
                website TEXT,                          -- Personal website
                avatar TEXT,                           -- Selected avatar image
                timezone TEXT,                         -- User's timezone
                datetime_format TEXT,                  -- Preferred datetime format
                is_active INTEGER DEFAULT 1            -- Account status
            )
        ''')
        print("✅ Table 'users' created/verified!")

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
        print("✅ Table 'quiz_results_enhanced' created/verified!")

        # Legacy quiz results table (kept for backward compatibility)
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
        print("✅ Table 'quiz_results' (legacy) created/verified!")

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
        print("✅ Table 'user_badges' created/verified!")

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
        print("✅ Table 'notifications' created/verified!")

        # Chat history table - stores user-chatbot interactions
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                language TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✅ Table 'chat_history' created/verified!")

        # Chat sessions table - organizes chat messages into sessions
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_message_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'chat_sessions' created/verified!")

        # Chat messages table - stores individual messages in a session
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
            )
        ''')
        print("✅ Table 'chat_messages' created/verified!")

        # Quiz questions table - stores all quiz questions
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,  -- Stored as JSON
                answer TEXT NOT NULL,
                question_type TEXT DEFAULT 'multiple_choice',
                points INTEGER DEFAULT 10,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Table 'quiz_questions' created/verified!")

        # Account activity table - tracks user activity
        conn.execute('''
            CREATE TABLE IF NOT EXISTS account_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'account_activity' created/verified!")

        # Study list table - stores user's study words
        conn.execute('''
            CREATE TABLE IF NOT EXISTS study_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                note TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'study_list' created/verified!")

        # Progress tracking table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                words_learned INTEGER DEFAULT 0,
                conversation_count INTEGER DEFAULT 0,
                accuracy_rate FLOAT DEFAULT 0.0,
                daily_streak INTEGER DEFAULT 0,
                last_activity_date DATE,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'user_progress' created/verified!")

        # Achievements table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT NOT NULL,
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        print("✅ Table 'achievements' created/verified!")

        # Create default admin user if it doesn't exist
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

        print("\n✅ Database initialization completed successfully!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)  # Make sure the server is accessible