# app.py - Language Learning Quiz Application
# This is the main application file that handles routes, user authentication, and quiz functionality

# Standard library imports
import os
import json
import random
import secrets
import smtplib
import sqlite3
import hashlib
import uuid
import traceback
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from random import sample, shuffle

# Third-party imports
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import google.generativeai as genai

# Define available languages based on quiz data
AVAILABLE_LANGUAGES = [
    'English', 'Spanish', 'Chinese', 'Malay',
    'French', 'Portuguese', 'Tamil'
]

# Initialize Flask application
app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'

# --- File Upload Configuration ---
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- SMTP Configuration for Email Notifications ---
# These settings are used for sending OTP and password reset emails
USE_CONSOLE_OTP = False  # Set to False to send actual emails

# SMTP settings for Gmail
smtp_server = "smtp.gmail.com"
smtp_port = 465  # SSL port for Gmail (changed from 587)
smtp_user = "kishenkish18@gmail.com"  # Replace with your actual email
smtp_password = "pxcu tasw ndev hnvf"  # Replace with your actual password

# --- Google Gemini AI Configuration ---
API_KEY = "AIzaSyC0M-x3-IiWaroDCwHo59vcF4GBWijhPC0"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- Level Requirements and Progression System ---
# This dictionary defines the points needed to reach each level and the badges awarded
# The progression system motivates users to continue learning and tracks their achievements
LEVEL_REQUIREMENTS = {
    'beginner': {'points': 300, 'badges': ['basic_vocab', 'simple_sentences']},
    'intermediate': {'points': 700, 'badges': ['grammar_fundamentals', 'common_phrases']},
    'advanced': {'points': 1500, 'badges': ['complex_grammar', 'idioms']}
}

# --- Points System Configuration ---
# These settings control how points are awarded during quizzes
def get_points_per_correct_answer(level):
    """Returns the base points for each correct answer based on level"""
    if level == 'advanced':
        return 5
    elif level == 'intermediate':
        return 3
    else:  # beginner
        return 1

def get_perfect_score_bonus(level):
    """Returns the bonus points for perfect score based on level"""
    if level == 'advanced':
        return 10
    elif level == 'intermediate':
        return 8
    else:  # beginner
        return 5

# --- Database Functions ---
# These functions handle database connections and common database operations

def get_db_connection():
    """
    Creates and returns a connection to the SQLite database with proper configuration.

    Returns:
        sqlite3.Connection: A configured database connection
    """
    # Get the absolute path to the database file
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    conn.execute('PRAGMA busy_timeout = 30000')  # 30 second timeout to avoid locking issues
    return conn

def get_user_id(email):
    """
    Retrieves a user's ID from their email address.

    Args:
        email (str): The user's email address

    Returns:
        int or None: The user's ID if found, None otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return user['id'] if user else None
    finally:
        # Ensure connection is closed even if an exception occurs
        if conn:
            conn.close()

def check_login(email, password, security_answer):
    """
    Validates user login credentials including security answer.

    Args:
        email (str): The user's email
        password (str): The user's password (plain text)
        security_answer (str): Answer to the security question

    Returns:
        dict or None: User data if authentication succeeds, None otherwise
    """
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password'], password) and user['security_answer'] == security_answer:
            return user
        return None

def register_user(username, email, password, security_answer):
    """
    Registers a new user in the database.

    Args:
        username (str): The user's chosen username
        email (str): The user's email address
        password (str): The user's password (will be hashed)
        security_answer (str): Answer to the security question

    Returns:
        bool: True if registration succeeded, False otherwise
    """
    with get_db_connection() as conn:
        # Check if email already exists
        if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return False

        try:
            conn.execute(
                "INSERT INTO users (username, email, password, security_answer) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), security_answer))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # This handles cases like username uniqueness constraint violations
            return False

# --- Helper Functions ---
# These utility functions support various features throughout the application

def get_language_icon(language):
    """
    Returns the appropriate Font Awesome icon name for a given language.
    These icons are used in the UI to visually represent different languages.

    Args:
        language (str): The language name

    Returns:
        str: The Font Awesome icon name for the language
    """
    icons = {
        'English': 'language',
        'Spanish': 'language',
        'French': 'language',
        'Chinese': 'yin-yang',
        'Japanese': 'torii-gate',
        'German': 'landmark',
        'Italian': 'pizza-slice',
        'Russian': 'monument',
        'Portuguese': 'globe-americas',
        'Arabic': 'mosque',
        'Malay': 'language',
        'Tamil': 'language'
    }
    # Default to 'globe' icon if language not found in the dictionary
    return icons.get(language, 'globe')

def get_progress_data(user_id):
    """
    Retrieves and calculates a user's progress data across all languages and difficulty levels.
    This function is central to the application's gamification system.

    Args:
        user_id (int): The user's ID

    Returns:
        dict: A comprehensive dictionary containing the user's progress data
    """
    with get_db_connection() as conn:
        # Get all quiz results for this user
        quizzes = conn.execute('''
            SELECT language, LOWER(difficulty) as difficulty, score, total,
                   timestamp, question_details, points_earned, streak_bonus, time_bonus
            FROM quiz_results_enhanced
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,)).fetchall()

        # Initialize data structures
        progress = {}                # Stores progress by language
        recent_activity = []         # Stores recent quiz activity
        total_points = 0             # Total points across all languages
        total_quizzes = 0            # Total number of quizzes taken
        streak_data = defaultdict(int)  # Tracks current streak by language

        # For new users with no quiz data, create default English language entry
        if not quizzes:
            progress['English'] = _create_default_language_progress('English')
            total_points = 0  # Explicitly set total points to 0 for new users

        # Process each quiz result
        for quiz in quizzes:
            lang = quiz['language']
            diff = quiz['difficulty']

            # If this is a new language for the user, initialize its progress data
            if lang not in progress:
                progress[lang] = _create_default_language_progress(lang)

            # Update points and quiz count for this difficulty level
            progress[lang]['levels'][diff]['points_earned'] += quiz['points_earned']
            progress[lang]['levels'][diff]['quizzes'] += 1

            # Update totals
            total_points += quiz['points_earned']
            total_quizzes += 1

            # Update streak data - a quiz is considered passed if score is at least 80%
            if quiz['score'] / quiz['total'] >= 0.8:  # Passed quiz
                streak_data[lang] += 1
                progress[lang]['streak'] = streak_data[lang]
                progress[lang]['highest_streak'] = max(progress[lang]['highest_streak'], streak_data[lang])
            else:
                streak_data[lang] = 0
                progress[lang]['streak'] = 0

            # Add to recent activity list
            recent_activity.append({
                'language': lang,
                'difficulty': diff,
                'score': quiz['score'],
                'total': quiz['total'],
                'passed': quiz['score']/quiz['total'] >= 0.8,
                'timestamp': quiz['timestamp'],
                'points_earned': quiz['points_earned'],
                'streak_bonus': quiz['streak_bonus'],
                'time_bonus': quiz['time_bonus']
            })

        # Calculate level progression and badges for each language
        for lang, data in progress.items():
            # Calculate total points across all difficulty levels
            lang_total_points = sum(level['points_earned'] for level in data['levels'].values())
            data['total_points'] = lang_total_points

            # Determine current level and points distribution
            _calculate_level_progression(data, lang_total_points)

            # Award badges based on progress
            _award_badges(data, lang_total_points)

        # Return the complete progress data dictionary
        return {
            'progress': progress,
            'recent_activity': recent_activity[:5],  # Last 5 quizzes
            'LEVEL_REQUIREMENTS': LEVEL_REQUIREMENTS,
            'total_points': total_points,
            'total_quizzes': total_quizzes,
            'POINTS_PER_CORRECT_ANSWER': get_points_per_correct_answer('beginner'),  # Default to beginner for new users
            'STREAK_BONUS': 0,  # Initialize streak bonus to 0 for new users
            'TIME_BONUS_MULTIPLIER': 0.2
        }

def _create_default_language_progress(language):
    """
    Helper function to create a default progress structure for a language.

    Args:
        language (str): The language name

    Returns:
        dict: Default progress structure for the language
    """
    return {
        'icon': get_language_icon(language),
        'levels': {
            'beginner': {'points_earned': 0, 'quizzes': 0},
            'intermediate': {'points_earned': 0, 'quizzes': 0},
            'advanced': {'points_earned': 0, 'quizzes': 0}
        },
        'badges': [],
        'current_level': 'beginner',
        'next_level': 'intermediate',
        'points_to_next': LEVEL_REQUIREMENTS['beginner']['points'],
        'streak': 0,
        'highest_streak': 0,
        'total_points': 0,
        'level_complete': False
    }

def _calculate_level_progression(data, total_points):
    """
    Helper function to calculate a user's level progression for a language.

    Args:
        data (dict): The language progress data to update
        total_points (int): Total points earned for this language
    """
    # Advanced level
    if total_points >= LEVEL_REQUIREMENTS['advanced']['points']:
        data['current_level'] = 'advanced'
        data['next_level'] = None
        data['points_to_next'] = 0
        data['level_complete'] = True

        # Distribute points across levels
        data['levels']['beginner']['points_earned'] = LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['intermediate']['points_earned'] = LEVEL_REQUIREMENTS['intermediate']['points'] - LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['advanced']['points_earned'] = total_points - LEVEL_REQUIREMENTS['intermediate']['points']

    # Intermediate level
    elif total_points >= LEVEL_REQUIREMENTS['intermediate']['points']:
        data['current_level'] = 'intermediate'
        data['next_level'] = 'advanced'
        data['points_to_next'] = max(0, LEVEL_REQUIREMENTS['advanced']['points'] - total_points)
        data['level_complete'] = False

        # Distribute points across levels
        data['levels']['beginner']['points_earned'] = LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['intermediate']['points_earned'] = total_points - LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['advanced']['points_earned'] = 0

    # Beginner level (lowest)
    else:
        data['current_level'] = 'beginner'
        data['next_level'] = 'intermediate'
        data['points_to_next'] = max(0, LEVEL_REQUIREMENTS['intermediate']['points'] - total_points)
        data['level_complete'] = False

        # All points go to beginner level
        data['levels']['beginner']['points_earned'] = total_points
        data['levels']['intermediate']['points_earned'] = 0
        data['levels']['advanced']['points_earned'] = 0

def _award_badges(data, total_points):
    """
    Helper function to award badges based on progress.

    Args:
        data (dict): The language progress data to update
        total_points (int): Total points earned for this language
    """
    data['badges'] = []

    # Vocabulary badges (beginner level)
    if data['levels']['beginner']['points_earned'] >= 100:  # 50% of beginner requirement
        data['badges'].append('basic_vocab')
    if data['levels']['beginner']['points_earned'] >= LEVEL_REQUIREMENTS['beginner']['points']:
        data['badges'].append('simple_sentences')

    # Grammar badges (intermediate level)
    if data['levels']['intermediate']['points_earned'] >= 250:  # 50% of intermediate requirement
        data['badges'].append('grammar_fundamentals')
    if data['levels']['intermediate']['points_earned'] >= LEVEL_REQUIREMENTS['intermediate']['points']:
        data['badges'].append('common_phrases')

    # Advanced language badges
    if data['levels']['advanced']['points_earned'] >= 500:  # 50% of advanced requirement
        data['badges'].append('complex_grammar')
    if data['levels']['advanced']['points_earned'] >= LEVEL_REQUIREMENTS['advanced']['points']:
        data['badges'].append('idioms')

    # Special streak badge for consistent performance
    if data['highest_streak'] >= 5:
        data['badges'].append('hot_streak')

def generate_otp():
    """
    Generates a random 6-digit One-Time Password (OTP) for user verification.

    Returns:
        str: A 6-digit OTP as a string
    """
    return str(random.randint(100000, 999999))

def send_otp(email, otp):
    """
    Sends an OTP verification code to the user's email.

    Args:
        email (str): The recipient's email address
        otp (str): The OTP code to send

    Returns:
        bool: True if the OTP was sent successfully, False otherwise
    """
    # Always print to console for debugging purposes
    print("\n" + "="*50)
    print(f"DEBUG - OTP CODE FOR {email}: {otp}")
    print("="*50 + "\n")

    # If using console OTP, don't try to send email
    if USE_CONSOLE_OTP:
        flash(f"OTP sent to {email}. For testing, check the console output.", 'info')
        return True

    # Send via email
    try:
        # Create email message with a professional format
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Your Verification Code"

        # Email body with the OTP in a clear format
        body = f"""
Hello,

Your verification code is: {otp}

This code is valid for 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
Language Learning App Team
        """
        msg.attach(MIMEText(body, 'plain'))

        # Send the email with better error handling
        server = None
        try:
            # Connect to the SMTP server using SSL
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            
            # Login and send
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email, msg.as_string())

            # Notify the user
            flash(f"Verification code sent to {email}. Please check your inbox and spam folder.", 'info')
            return True

        finally:
            # Make sure to close the connection even if an error occurs
            if server:
                server.quit()

    except smtplib.SMTPAuthenticationError:
        # Specific error for authentication issues
        print("SMTP Authentication Error: Invalid username or password")
        flash('Email authentication failed. Please check your email settings.', 'error')
        return False

    except smtplib.SMTPException as e:
        # General SMTP errors
        print(f"SMTP Error: {str(e)}")
        flash('Error sending verification code. Please try again later.', 'error')
        return False

    except Exception as e:
        # Any other errors
        print(f"Unexpected error sending OTP: {str(e)}")
        flash('Error sending verification code. Please try again or contact support.', 'error')
        return False

def add_notification(user_id, notification_message):
    """
    Adds a notification for a user in the database.
    These notifications appear in the user's notification center.

    Args:
        user_id (int): The user's ID
        notification_message (str): The notification message text
    """
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, message, timestamp, is_read) VALUES (?, ?, ?, 0)",
            (user_id, notification_message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

# --- Import application modules ---
# These imports are placed here to avoid circular imports
from scripts.quiz_data import QUIZ_DATA  # Pre-defined quiz questions by language and difficulty

# --- Application Routes ---
# These functions handle HTTP requests and render the appropriate templates

@app.route('/')
def index():
    """
    Root route - redirects to the login page.
    """
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login with email, password, and security answer.
    On successful authentication, sends an OTP for two-factor authentication.
    """
    # If user is already logged in and verified, redirect to dashboard
    if 'username' in session and session.get('verified'):
        return redirect(url_for('dashboard'))

    # Handle login form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        security_answer = request.form.get('security_answer')

        # Validate that all required fields are provided
        if not all([email, password, security_answer]):
            flash("All fields are required", 'error')
            return redirect(url_for('login'))

        # Authenticate the user
        user = check_login(email, password, security_answer)

        if user:
            # Store user information in session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = email
            session['verified'] = False  # Not fully verified until OTP is confirmed

            # Generate and send OTP for two-factor authentication
            otp = generate_otp()
            session['otp'] = otp

            # Send OTP via email
            if not send_otp(email, otp):
                # If sending fails, show error and redirect back to login
                flash("Failed to send verification code. Please try again.", "error")
                return redirect(url_for('login'))

            return redirect(url_for('verify_otp'))
        else:
            flash("Invalid email, password, or security answer", 'error')
            return redirect(url_for('login'))

    # Display login form for GET requests
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """
    Verifies the OTP entered by the user for two-factor authentication.
    """
    # Ensure user has started the login process
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        otp_entered = request.form['otp']

        # Verify the OTP matches what was sent
        if otp_entered == session.get('otp'):
            # Complete the authentication process
            session['verified'] = True

            # Add a notification for the user
            add_notification(session['user_id'], "You logged in successfully")

            return redirect(url_for('dashboard'))
        else:
            flash("Invalid OTP code. Please try again.", 'error')

    # Display OTP verification form
    return render_template('verify_otp.html')

@app.route('/resend_otp', methods=['GET'])
def resend_otp():
    """
    Resends the OTP to the user's email if they didn't receive it.
    """
    if 'email' in session:
        # Generate a new OTP and update the session
        otp = generate_otp()
        session['otp'] = otp

        # Send OTP via email
        if send_otp(session['email'], otp):
            flash("A new verification code has been sent to your email.", 'info')
        else:
            flash("Failed to send verification code. Please try again.", 'error')

    return redirect(url_for('verify_otp'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Handles password reset requests by sending a reset link to the user's email.
    """
    if request.method == 'POST':
        email = request.form['email']

        # Check if the email exists in the database
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            if user:
                # Generate a secure reset token
                reset_token = secrets.token_urlsafe(16)

                # Store the reset token in the database
                with get_db_connection() as conn:
                    conn.execute("UPDATE users SET reset_token = ? WHERE email = ?", (reset_token, email))
                    conn.commit()

                # Send password reset email
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = email
                msg['Subject'] = 'Password Reset Request'

                # Create the reset link
                reset_link = f"http://localhost:5000/reset_password/{reset_token}"
                body = f"""
                You requested a password reset for your Language Learning Quiz account.

                Click the link below to reset your password:
                {reset_link}

                If you did not request this reset, please ignore this email.
                """
                msg.attach(MIMEText(body, 'plain'))

                # For testing, print the reset link to console instead of sending email
                if USE_CONSOLE_OTP:
                    print("\n" + "="*50)
                    print(f"PASSWORD RESET LINK FOR {email}: {reset_link}")
                    print("="*50 + "\n")
                else:
                    # Send the email
                    try:
                        server = smtplib.SMTP(smtp_server, smtp_port)
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.sendmail(smtp_user, email, msg.as_string())
                        server.quit()
                    except Exception as e:
                        print(f"Error sending password reset email: {str(e)}")
                        flash("Error sending password reset email. Please try again later.", "error")
                        return redirect(url_for('forgot_password'))

                flash('Check your email for the password reset link.', 'info')
                return redirect(url_for('login'))
            else:
                flash("Email not found in our records.", 'error')

    # Display password reset request form
    return render_template('forgot_password.html')

@app.route('/reset_password/<reset_token>', methods=['GET', 'POST'])
def reset_password(reset_token):
    """
    Allows users to set a new password using a valid reset token.

    Args:
        reset_token (str): The unique token from the reset link
    """
    if request.method == 'POST':
        new_password = request.form['new_password']

        # Hash the new password and update the user's record
        hashed_password = generate_password_hash(new_password)

        with get_db_connection() as conn:
            # Update password and clear the reset token
            result = conn.execute(
                "UPDATE users SET password = ?, reset_token = NULL WHERE reset_token = ?",
                (hashed_password, reset_token)
            )
            conn.commit()

            # Check if a user was actually updated
            if result.rowcount > 0:
                flash("Your password has been successfully updated.", 'success')
            else:
                flash("Invalid or expired reset token.", 'error')

        return redirect(url_for('login'))

    # Display password reset form
    return render_template('reset_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles new user registration.
    """
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        security_answer = request.form['security_answer']

        # Attempt to register the user
        success = register_user(username, email, password, security_answer)

        if success:
            flash("Registration successful! Please log in.", 'success')
            return redirect(url_for('login'))
        else:
            flash("Registration failed. Email or username already exists.", 'error')

    # Display registration form
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """
    Displays the user's dashboard with progress information and notifications.
    This is the main page after login.
    """
    # Ensure user is logged in and verified
    if 'username' not in session or not session.get('verified'):
        return redirect(url_for('login'))

    # Get unread notification count
    with get_db_connection() as conn:
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (session['user_id'],)
        ).fetchone()[0]

    # Get user's progress data
    progress_data = get_progress_data(session['user_id'])

    # Render dashboard template with user data
    return render_template('dashboard.html',
                         username=session['username'],
                         notification_count=notification_count,
                         progress=progress_data)

@app.route('/logout')
def logout():
    """
    Logs out the user by clearing their session.
    """
    session.clear()
    flash("You have been logged out successfully.", 'info')
    return redirect(url_for('login'))

@app.route('/progress')
def progress():
    """
    Displays detailed progress information for the user across all languages.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get user's progress data
    progress_data = get_progress_data(session['user_id'])

    # Render progress template with detailed information
    return render_template('progress.html',
                         username=session['username'],
                         progress=progress_data,
                         LEVEL_REQUIREMENTS=LEVEL_REQUIREMENTS)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Handles user profile settings and updates.
    Allows users to change their profile information, password, preferences, and account status.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get current user data
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (session['username'],)).fetchone()
    
    # For avatar selection, get available avatars from static/avatars
    avatars = []
    avatars_dir = os.path.join('static', 'avatars')
    if os.path.exists(avatars_dir):
        avatars = [f for f in os.listdir(avatars_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    # Handle form submission for profile updates
    if request.method == 'POST':
        action = request.form.get('action', 'save_profile')
        
        # Profile update
        if action == 'save_profile':
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            location = request.form.get('location')
            website = request.form.get('website')
            bio = request.form.get('bio')
            
            # Process URLs
            urls = []
            for key, values in request.form.lists():
                if key == 'urls':
                    for value in values:
                        if value and value.strip():
                            urls.append(value.strip())
            # Always set urls_str (could be empty string)
            urls_str = '\n'.join(urls) if urls else ''
            
            # Avatar/profile picture handling
            profile_pic_filename = None
            selected_avatar = request.form.get('selected_avatar')
            
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename and allowed_file(file.filename):
                    # Secure the filename and save the file
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_pic_filename = filename

            try:
                # Prepare update data
                update_data = {}
                
                # Add all fields to update data if they have values
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
                # Always include URLs to allow them to be cleared
                update_data['urls'] = urls_str
                
                # Handle avatar selection vs uploaded profile picture
                if selected_avatar:
                    update_data['avatar'] = selected_avatar
                    update_data['profile_picture'] = None  # Clear profile_picture if avatar is chosen
                elif profile_pic_filename:
                    update_data['profile_picture'] = profile_pic_filename
                    update_data['avatar'] = None  # Clear avatar if uploading a new picture

                # Only update if we have data to update
                if update_data:
                    # Build the SQL update statement
                    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                    values = list(update_data.values())
                    values.append(session['username'])

                    # Execute the update
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
                
        # Password change
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
                # Update password
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
                
        # Save preferences
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
                    # Build the SQL update statement
                    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                    values = list(update_data.values())
                    values.append(session['username'])

                    # Execute the update
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

    # Display settings form with current user data
    return render_template('settings.html',
                         username=session['username'],
                         user=user,
                         avatars=avatars)

@app.route('/notifications')
def notifications():
    """
    Displays the user's notification center with both read and unread notifications.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Get both unread and read notifications
    with get_db_connection() as conn:
        # Get unread notifications
        unread_notifications = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY timestamp DESC",
            (user_id,)
        ).fetchall()

        # Get read notifications
        read_notifications = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND is_read = 1 ORDER BY timestamp DESC LIMIT 20",
            (user_id,)
        ).fetchall()

    # Render notifications page
    return render_template('notifications.html',
                        unread_notifications=unread_notifications,
                        read_notifications=read_notifications)

@app.route('/notifications/count')
def notifications_count():
    """
    API endpoint that returns the count of unread notifications.
    Used for updating the notification badge in the UI.
    """
    if 'username' not in session:
        return jsonify({'count': 0})

    # Get count of unread notifications
    with get_db_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (session['user_id'],)
        ).fetchone()[0]

    return jsonify({'count': count})

@app.route('/notifications/json')
def notifications_json():
    """
    API endpoint that returns all notifications as JSON.
    Used for AJAX updates of the notification center.
    """
    if 'username' not in session:
        return jsonify([])

    user_id = session['user_id']

    # Get all notifications for this user
    with get_db_connection() as conn:
        notifications = conn.execute(
            "SELECT id, message, timestamp, is_read FROM notifications WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
            (user_id,)
        ).fetchall()

    # Convert to a list of dictionaries for JSON serialization
    notifications_list = [{
        'id': notification['id'],
        'message': notification['message'],
        'timestamp': notification['timestamp'],
        'is_read': bool(notification['is_read'])
    } for notification in notifications]

    return jsonify(notifications_list)

@app.route('/mark_notification_read', methods=['POST'])
def mark_notification_read():
    """
    API endpoint to mark a single notification as read.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403

    # Get notification ID from request
    data = request.get_json()
    notification_id = data.get('notification_id')

    # Validate notification ID
    if not notification_id:
        return jsonify({'status': 'error', 'message': 'Missing notification_id'}), 400

    # Mark notification as read
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?',
            (notification_id, session['user_id'])
        )
        conn.commit()

    return jsonify({'status': 'success'})

@app.route('/mark_all_notifications_read', methods=['POST'])
def mark_all_notifications_read():
    """
    API endpoint to mark all notifications as read for the current user.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 403

    user_id = session['user_id']

    # Mark all notifications as read
    with get_db_connection() as conn:
        conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
        conn.commit()

    return jsonify({'status': 'success'})

@app.route('/quiz')
def quiz():
    """
    Displays the quiz selection page where users can choose a language and difficulty level.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get user's progress data for displaying their current levels
    progress_data = get_progress_data(session['user_id'])

    # List of available languages for quizzes
    languages = [
        'English', 'Chinese', 'Malay', 'Spanish',
        'French', 'Portuguese', 'Tamil'
    ]

    # Render quiz selection page
    return render_template('quiz.html',
                         languages=languages,
                         progress=progress_data)

@app.route('/quiz/<language>/<difficulty>')
def quiz_language_difficulty(language, difficulty):
    """
    Generates and displays quiz questions for a specific language and difficulty level
    using pre-defined questions from quiz_data.py.

    Args:
        language (str): The language for the quiz
        difficulty (str): The difficulty level (beginner, intermediate, advanced)
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Check if language exists in QUIZ_DATA
    if language not in QUIZ_DATA:
        flash(f"Language '{language}' not available", 'error')
        return redirect(url_for('quiz'))

    # Check if difficulty exists for this language
    if difficulty not in QUIZ_DATA.get(language, {}):
        flash(f"Difficulty level '{difficulty}' not available for {language}", 'error')
        return redirect(url_for('quiz'))

    # Get the raw questions for this language and difficulty
    raw_questions = QUIZ_DATA.get(language, {}).get(difficulty, [])

    if not raw_questions:
        flash(f"No {difficulty} questions available for {language} yet", 'info')
        return redirect(url_for('quiz'))

    # Shuffle questions for variety and limit to 10 questions
    shuffled_questions = sample(raw_questions, min(len(raw_questions), 10))

    # Process the questions into the format needed for the template
    questions = _process_questions(shuffled_questions, ai_generated=False)

    # Render the quiz with pre-defined questions
    return render_template('quiz_questions.html',
                        questions=questions,
                        difficulty=difficulty,
                        language=language,
                        ai_generated=False)

def _process_quiz_questions(form_data, language, difficulty, ai_generated=False):
    """
    Helper function to process quiz questions from form data.

    Args:
        form_data (ImmutableMultiDict): Form data from the request
        language (str): The quiz language
        difficulty (str): The quiz difficulty level
        ai_generated (bool): Whether the quiz used AI-generated questions (always False now)

    Returns:
        list: Processed question objects
    """
    # Get the order of questions as they were displayed to the user
    question_order = form_data.get('question_order', '')
    question_numbers = [int(num) for num in question_order.split(',') if num.strip()]

    # Get all questions for this language and difficulty
    all_questions = QUIZ_DATA.get(language, {}).get(difficulty, [])

    # If we have question order, use it to match questions with answers
    if question_numbers:
        # Create a mapping of question number to the actual question
        displayed_questions = []
        for i, q_num in enumerate(question_numbers, 1):
            if 1 <= q_num <= len(all_questions):
                question = all_questions[q_num - 1].copy()  # Make a copy to avoid modifying the original

                # Special handling for matching questions
                if question.get('type') == 'matching' and 'pairs' in question:
                    # Ensure the correct_answer field is set for matching questions
                    pairs = question['pairs']
                    formatted_answer = ", ".join([f"{left} → {right}" for left, right in pairs])
                    question['formatted_answer'] = formatted_answer

                displayed_questions.append(question)

        return displayed_questions
    else:
        # Fall back to original behavior if question_order is missing
        return all_questions

def _validate_answer(question_type, user_answer, correct_answer, form_data, question_number):
    """
    Validates a user's answer against the correct answer based on question type.

    Args:
        question_type (str): The type of question (multiple_choice, fill_blank, etc.)
        user_answer (str): The user's submitted answer
        correct_answer (str): The correct answer
        form_data (ImmutableMultiDict): The form data containing additional question information
        question_number (int): The question number

    Returns:
        tuple: (is_correct, formatted_user_answer, correct_answer)
    """
    import re

    # Default to incorrect
    is_correct = False
    formatted_user_answer = user_answer if user_answer else "No answer"

    # Multiple choice questions - exact match
    if question_type in ['multiple_choice', 'multiple_choice_image', 'error_spotting',
                        'context_responses', 'mini_dialogue', 'phrase_completion',
                        'idiom_interpretation', 'cultural_nuances', 'news_headline',
                        'debate_style', 'complex_rephrasing', 'audio_recognition',
                        'basic_vocab', 'simple_sentences', 'context_responses']:
        # For multiple choice, just do a direct comparison
        is_correct = (user_answer == correct_answer)

    # Text input questions - flexible matching
    elif question_type in ['fill_blank', 'grammar_application']:
        # For text input, do case-insensitive comparison and strip whitespace
        if user_answer and correct_answer:
            user_clean = user_answer.lower().strip()
            correct_clean = correct_answer.lower().strip()
            is_correct = (user_clean == correct_clean)

            # If still not correct, try removing punctuation
            if not is_correct:
                user_flexible = re.sub(r'[^\w\s]', '', user_clean).strip()
                correct_flexible = re.sub(r'[^\w\s]', '', correct_clean).strip()
                is_correct = (user_flexible == correct_flexible)

    # Matching questions - complex validation
    elif question_type == 'matching':
        # For matching questions, we need to parse the user's matches
        if user_answer:
            # Get the left and right items
            left_items_str = form_data.get(f'left_items_{question_number}', '')
            right_items_str = form_data.get(f'right_items_{question_number}', '')
            pairs_str = form_data.get(f'pairs_{question_number}', '')

            if left_items_str and right_items_str and pairs_str:
                left_items = left_items_str.split('|')
                right_items = right_items_str.split('|')

                # Parse the correct pairs
                correct_pairs = []
                for pair_item in pairs_str.split('|'):
                    if ':' in pair_item:
                        left, right = pair_item.split(':', 1)
                        correct_pairs.append((left.strip(), right.strip()))

                # Create a map of correct matches
                correct_map = {left: right for left, right in correct_pairs}

                # Parse the user's matches
                user_matches = {}
                user_pairs = []

                for match in user_answer.split(','):
                    if ':' in match:
                        try:
                            left_id, right_id = map(int, match.split(':'))
                            if 0 <= left_id < len(left_items) and 0 <= right_id < len(right_items):
                                left_item = left_items[left_id]
                                right_item = right_items[right_id]
                                user_matches[left_item] = right_item
                                user_pairs.append(f"{left_item} → {right_item}")
                        except (ValueError, IndexError):
                            pass

                # Check if all pairs are matched correctly
                total_correct = 0
                for left, right in correct_map.items():
                    if left in user_matches and user_matches[left] == right:
                        total_correct += 1

                # Consider correct if all pairs are matched correctly
                is_correct = (total_correct == len(correct_pairs) and len(user_matches) == len(correct_pairs))

                # Format the user's answer for display
                formatted_user_answer = ", ".join(user_pairs) if user_pairs else "Incomplete matches"

                # Format the correct answer for display
                correct_answer = ", ".join([f"{left} → {right}" for left, right in correct_pairs])
            else:
                # If we don't have the necessary data, set default values
                is_correct = False
                formatted_user_answer = "Incomplete matches"

                # Try to get correct answer from the hidden field
                correct_answer_field = form_data.get(f'correct_answer_{question_number}', '')
                if correct_answer_field:
                    correct_answer = correct_answer_field
                else:
                    correct_answer = "Could not determine correct matches"
        else:
            # If no user answer, set default values
            is_correct = False
            formatted_user_answer = "No matches made"

            # Try to get correct pairs from the form data
            pairs_str = form_data.get(f'pairs_{question_number}', '')
            if pairs_str:
                correct_pairs = []
                for pair_item in pairs_str.split('|'):
                    if ':' in pair_item:
                        left, right = pair_item.split(':', 1)
                        correct_pairs.append((left.strip(), right.strip()))
                correct_answer = ", ".join([f"{left} → {right}" for left, right in correct_pairs])
            else:
                # Try to get correct answer from the hidden field
                correct_answer_field = form_data.get(f'correct_answer_{question_number}', '')
                if correct_answer_field:
                    correct_answer = correct_answer_field
                else:
                    correct_answer = "Could not determine correct matches"

    # Sentence construction questions
    elif question_type == 'sentence_construction':
        # For sentence construction, compare the sentences
        if user_answer and correct_answer:
            user_clean = user_answer.lower().strip()
            correct_clean = correct_answer.lower().strip()
            is_correct = (user_clean == correct_clean)

            # If still not correct, try removing punctuation and normalizing spaces
            if not is_correct:
                user_flexible = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', user_clean)).strip()
                correct_flexible = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', correct_clean)).strip()
                is_correct = (user_flexible == correct_flexible)

    return is_correct, formatted_user_answer, correct_answer

def _process_questions(raw_questions, ai_generated=False):
    """
    Helper function to process quiz questions into the format needed for templates.

    Args:
        raw_questions (list): List of question dictionaries
        ai_generated (bool): Kept for backward compatibility, always False now

    Returns:
        list: Processed questions ready for the template
    """
    questions = []

    for i, q in enumerate(raw_questions, 1):
        # Create base question data
        question_data = {
            'number': i,
            'text': q['question'],
            'type': q['type'],
            'points': q.get('points', 10),
            'time_limit': q.get('time_limit', 30),
            'ai_generated': False  # Always set to False since AI generation is removed
        }

        # Process based on question type
        if q['type'] in ['multiple_choice', 'multiple_choice_image', 'error_spotting',
                        'context_responses', 'mini_dialogue', 'phrase_completion',
                        'idiom_interpretation', 'cultural_nuances', 'news_headline',
                        'debate_style', 'complex_rephrasing', 'audio_recognition',
                        'basic_vocab', 'simple_sentences']:
            # Handle multiple choice type questions
            options = sorted(q['options'])  # Sort options alphabetically
            question_data.update({
                'options': options,
                'answer': q['answer']
            })

            # Add explanation for question types that have it
            if 'explanation' in q and q['type'] in ['error_spotting', 'idiom_interpretation', 'cultural_nuances']:
                question_data['explanation'] = q['explanation']

            # Add audio file for audio recognition questions
            if q['type'] == 'audio_recognition' and 'audio_file' in q:
                question_data['audio_file'] = q['audio_file']

        elif q['type'] == 'fill_blank' or q['type'] == 'grammar_application':
            # Handle fill-in-the-blank type questions
            question_data.update({
                'answer': q['answer'],
                'hint': q.get('hint', '')
            })

        elif q['type'] == 'matching' or q['type'] == 'word_matching':
            # Handle matching type questions
            pairs = q['pairs']
            if q.get('shuffled', True):
                left_items = [pair[0] for pair in pairs]
                right_items = [pair[1] for pair in pairs]
                shuffle(right_items)

                # Pre-format the correct answer for matching questions
                formatted_answer = ", ".join([f"{left} → {right}" for left, right in pairs])

                question_data.update({
                    'left_items': left_items,
                    'right_items': right_items,
                    'pairs': pairs,  # Store the original pairs for correct answer
                    'correct_matches': pairs,
                    'answer': formatted_answer  # Store formatted answer in the answer field
                })

        elif q['type'] == 'sentence_construction':
            # Handle sentence construction type questions
            question_data.update({
                'words': q['words'],
                'answer': q['answer']
            })

        questions.append(question_data)

    return questions

@app.route('/quiz/<difficulty>')
def quiz_level(difficulty):
    """
    Redirects to the language-specific quiz route.
    This route is used when only the difficulty is specified in the URL.

    Args:
        difficulty (str): The difficulty level (beginner, intermediate, advanced)
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get language from query parameters, default to English
    language = request.args.get('language', 'English')

    # Check if AI-generated questions are requested
    use_ai = request.args.get('ai', 'false').lower() == 'true'

    # Redirect to the language-specific route with appropriate parameters
    return redirect(url_for('quiz_language_difficulty',
                          language=language,
                          difficulty=difficulty,
                          ai='true' if use_ai else 'false'))

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    """
    Handles quiz submission, scoring, and recording results.
    This is a complex route that processes user answers, calculates scores and bonuses,
    and updates the user's progress and achievements.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get basic quiz information
    language = request.form.get('language')
    difficulty = request.form.get('difficulty')
    form_data = request.form

    # Check if this was an AI-generated quiz
    ai_generated = form_data.get('ai_generated', 'false').lower() == 'true'

    # Process the questions based on whether they were AI-generated or not
    # Note: We don't need the returned questions, we just need to validate the form data
    _ = _process_quiz_questions(form_data, language, difficulty, ai_generated)

    # Initialize scoring variables
    score = 0               # Number of correct answers
    results = []            # Detailed results for each question
    question_details = []   # Question details for database storage
    total_time = 0          # Total time spent on the quiz
    correct_streak = 0      # Current streak of correct answers
    max_streak = 0          # Maximum streak achieved

    # Get the total number of questions from the form data
    question_count = 0
    for key in form_data.keys():
        if key.startswith('question_text_'):
            question_count += 1

    # Process each question directly from the form data
    for i in range(1, question_count + 1):
        # Get basic question data
        question_text = form_data.get(f'question_text_{i}', 'Unknown Question')
        correct_answer = form_data.get(f'correct_answer_{i}', '')
        question_type = form_data.get(f'question_type_{i}', 'multiple_choice')
        user_answer = form_data.get(f'q_{i}', '')
        time_taken = int(form_data.get(f'time_{i}', 0))
        total_time += time_taken

        # Default values
        is_correct = False
        formatted_user_answer = user_answer if user_answer else "No answer"

        # Validate the answer based on question type
        is_correct, formatted_user_answer, correct_answer = _validate_answer(
            question_type, user_answer, correct_answer, form_data, i
        )

        # Update score and streak
        if is_correct:
            score += 1
            correct_streak += 1
            max_streak = max(max_streak, correct_streak)
        else:
            correct_streak = 0

        # Get options for multiple choice questions
        options = []
        if question_type in ['multiple_choice', 'multiple_choice_image']:
            options_str = form_data.get(f'options_{i}', '')
            if options_str:
                options = options_str.split('|')

        # Add to results for display to user
        results.append({
            'question': question_text,
            'user_answer': formatted_user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'options': options,
            'time_taken': time_taken,
            'question_type': question_type
        })

        # Add to question details for database storage
        question_details.append({
            'question': question_text,
            'user_answer': formatted_user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'options': options,
            'time_taken': time_taken,
            'points': 10,  # Default to 10 points
            'question_type': question_type
        })

    # Calculate quiz statistics
    total_questions = question_count
    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    passed = 1 if percentage >= 80 else 0  # Pass threshold is 80%

    # Calculate points with bonuses
    base_points = score * get_points_per_correct_answer(difficulty)
    streak_bonus = (max_streak // 3) * get_perfect_score_bonus(difficulty)  # Bonus every 3 correct in a row
    time_bonus = 0

    # Time bonus for quick answers
    avg_time = total_time / total_questions if total_questions > 0 else 0
    if avg_time < 10:
        time_bonus = base_points * 0.2 * (1 - (avg_time / 10))

    points_earned = int(base_points + streak_bonus + time_bonus)

    # Get user's current rank for this language before adding new points
    current_progress = get_progress_data(session['user_id'])
    lang_progress = current_progress['progress'].get(language, {})
    current_level = lang_progress.get('current_level', 'beginner') if lang_progress else 'beginner'
    
    # Determine if user should earn points based on their current level and quiz difficulty
    should_award_points = True
    if current_level == 'intermediate' and difficulty == 'beginner':
        # Intermediate users don't get points for beginner quizzes
        should_award_points = False
    elif current_level == 'advanced' and difficulty != 'advanced':
        # Advanced users only get points for advanced quizzes
        should_award_points = False
    
    # Set points to 0 if user shouldn't be awarded points
    if not should_award_points:
        points_earned = 0
        streak_bonus = 0
        time_bonus = 0

    # Determine if achievements were unlocked
    achievements = []

    # Achievement: Language Proficiency
    if percentage >= 70:
        achievements.append({
            "name": f"{difficulty.capitalize()} {language} Proficiency",
            "icon": "medal",
            "description": f"Scored over 70% on a {difficulty} {language} quiz"
        })

    # Achievement: Hot Streak
    if max_streak >= 5:
        achievements.append({
            "name": "Hot Streak",
            "icon": "fire-alt",
            "description": f"{max_streak} correct answers in a row!"
        })

    # Achievement: Speed Demon
    if avg_time < 10 and percentage > 60:
        achievements.append({
            "name": "Speed Demon",
            "icon": "tachometer-alt",
            "description": "Fast and accurate answers!"
        })

    try:
        # Store quiz results in the database
        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO quiz_results_enhanced
                (user_id, language, difficulty, score, total, percentage, passed,
                 question_details, points_earned, streak_bonus, time_bonus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session['user_id'], language, difficulty, score, total_questions,
                 percentage, passed, json.dumps(question_details), points_earned, streak_bonus, time_bonus)
            )
            conn.commit()

        # Check for level up by getting updated progress data
        progress = get_progress_data(session['user_id'])
        lang_progress = progress['progress'].get(language, {})

        # Check if user just reached a level threshold
        just_leveled_up = False
        if lang_progress:
            # Get the total points for this language
            current_total_points = lang_progress.get('total_points', 0)
            # Calculate what the total points were before this quiz
            total_points_before = current_total_points - points_earned

            # Check if this quiz pushed the user over a level threshold
            if (total_points_before < LEVEL_REQUIREMENTS['intermediate']['points'] and
                current_total_points >= LEVEL_REQUIREMENTS['intermediate']['points']):
                just_leveled_up = True
            elif (total_points_before < LEVEL_REQUIREMENTS['advanced']['points'] and
                  current_total_points >= LEVEL_REQUIREMENTS['advanced']['points']):
                just_leveled_up = True

        # Send level up notification if user reached a new level
        if lang_progress and (lang_progress.get('points_to_next', 1) <= 0 or just_leveled_up):
            add_notification(
                session['user_id'],
                f"Level Up! You've reached {lang_progress['current_level']} in {language}"
            )

        # Send quiz completion notification
        add_notification(
            session['user_id'],
            f"You scored {score}/{total_questions} ({percentage:.0f}%) in {language} {difficulty} quiz"
        )

        # Check for new badges
        new_badges = []
        if score == total_questions:
            new_badges.append("perfect_score")  # Perfect score badge
        if max_streak >= 5:
            new_badges.append("hot_streak")     # Hot streak badge

        # Award badges and send notifications
        with get_db_connection() as conn:
            for badge in new_badges:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_badges (user_id, language, badge_id) VALUES (?, ?, ?)",
                        (session['user_id'], language, badge)
                    )
                    conn.commit()

                    # Notify user about new badge
                    badge_name = badge.replace('_', ' ').title()
                    add_notification(session['user_id'], f"New badge earned: {badge_name}!")
                except Exception as e:
                    print(f"Error saving badge: {e}")

    except Exception as e:
        print(f"Error saving quiz results: {e}")
        flash("Error saving your quiz results", 'error')

    # Return the results page with all the quiz data
    return render_template('quiz_results.html',
                         # Quiz score information
                         score=score,
                         total=total_questions,
                         percentage=percentage,
                         results=results,

                         # Quiz metadata
                         language=language,
                         difficulty=difficulty,

                         # Points and bonuses
                         points_earned=points_earned,
                         streak_bonus=streak_bonus,
                         time_bonus=time_bonus,
                         
                         # User level info
                         current_level=current_level,

                         # Level up information
                         level_up=lang_progress.get('points_to_next', 1) <= 0 if lang_progress else False,
                         new_level=lang_progress.get('current_level') if lang_progress else None,

                         # Achievements and statistics
                         achievements=achievements,
                         max_streak=max_streak,
                         avg_time=avg_time)

@app.route('/quiz_details/<int:quiz_id>')
def quiz_details(quiz_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        quiz = conn.execute('''
            SELECT id, language, difficulty, score, total, percentage, passed,
                   timestamp, question_details, points_earned, streak_bonus, time_bonus
            FROM quiz_results_enhanced
            WHERE id = ? AND user_id = ?
        ''', (quiz_id, session['user_id'])).fetchone()

    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('progress'))

    quiz_data = dict(quiz)
    quiz_data['questions'] = json.loads(quiz_data['question_details'])

    return render_template('quiz_details.html',
                         quiz=quiz_data,
                         username=session['username'])

@app.route('/get_quiz_progress/<int:user_id>')
def get_quiz_progress(user_id):
    if 'username' not in session:
        return jsonify([])

    with get_db_connection() as conn:
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

# --- Admin Routes ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """
    Handles admin login authentication.
    In a production environment, this should use proper authentication with database-stored credentials.
    """
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if user exists and is an admin
        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_admin = 1",
                (email,)
            ).fetchone()

            if user and check_password_hash(user['password'], password):
                session['admin'] = True
                session['admin_id'] = user['id']
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid email or password for admin.", 'error')

    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    """
    Admin dashboard displaying all users and their information.
    Only accessible to authenticated admins.
    """
    if 'admin' not in session:
        flash("You must be logged in as an admin to access this page.", 'error')
        return redirect(url_for('admin_login'))

    # Get all users from the database
    with get_db_connection() as conn:
        users = conn.execute("SELECT * FROM users").fetchall()

    return render_template('admin_dashboard.html', 
                         users=users,
                         languages=AVAILABLE_LANGUAGES,
                         quiz_data=QUIZ_DATA)  # Pass quiz data to template

@app.route('/admin/reset_progress/<int:user_id>', methods=['POST'])
def admin_reset_progress(user_id):
    """Reset a user's progress"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            # Delete quiz results
            conn.execute("DELETE FROM quiz_results_enhanced WHERE user_id = ?", (user_id,))
            # Delete badges
            conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error resetting progress: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
def admin_toggle_admin(user_id):
    """Toggle admin status for a user"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get the action from the request body
        data = request.get_json()
        make_admin = data.get('make_admin', True)  # Default to making admin if not specified

        with get_db_connection() as conn:
            # Get current admin status
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Don't allow removing admin status from the last admin
            if not make_admin:  # If we're trying to remove admin
                admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
                if admin_count <= 1 and user['is_admin'] == 1:
                    return jsonify({'error': 'Cannot remove the last admin'}), 400

            # Update admin status
            conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if make_admin else 0, user_id))
            conn.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        print(f"Error updating admin status: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    """Delete a user and all their data"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            # Delete user's data from all related tables
            conn.execute("DELETE FROM quiz_results_enhanced WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/admin/add_question', methods=['POST'])
def admin_add_question():
    """Add a new quiz question"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        # Get form data
        language = request.form.get('language')
        difficulty = request.form.get('difficulty')
        question = request.form.get('question')
        options_text = request.form.get('options', '')
        correct_answer = request.form.get('correct_answer')

        # Input validation
        if not all([language, difficulty, question, options_text, correct_answer]):
            return jsonify({'error': 'All fields are required'}), 400

        # Process options - split by newline and clean
        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]

        # Validate options
        if len(options) < 2:
            return jsonify({'error': 'At least two options are required'}), 400

        # Validate correct answer is in options
        if correct_answer not in options:
            return jsonify({'error': 'Correct answer must be one of the options'}), 400

        # Store in database
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO quiz_questions 
                (language, difficulty, question, options, answer)
                VALUES (?, ?, ?, ?, ?)
            ''', (language, difficulty, question, json.dumps(options), correct_answer))
            conn.commit()

        # Reload quiz data from database
        load_quiz_data()
        
        return jsonify({
            'success': True,
            'message': 'Question added successfully'
        }), 200

    except Exception as e:
        print(f"Error adding question: {str(e)}")
        return jsonify({'error': f'Error adding question: {str(e)}'}), 500

@app.route('/admin/edit_question/<language>/<difficulty>/<int:question_index>', methods=['POST'])
def edit_question(language, difficulty, question_index):
    """Edit a specific quiz question"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        # Get form data
        question = request.form.get('question')
        options_text = request.form.get('options', '')
        correct_answer = request.form.get('correct_answer')

        # Input validation
        if not all([question, options_text, correct_answer]):
            return jsonify({'error': 'All fields are required'}), 400

        # Process options - split by newline and clean
        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]

        # Validate options
        if len(options) < 2:
            return jsonify({'error': 'At least two options are required'}), 400

        # Validate correct answer is in options
        if correct_answer not in options:
            return jsonify({'error': 'Correct answer must be one of the options'}), 400

        # Update in database
        with get_db_connection() as conn:
            # Get the question ID
            question_id = conn.execute('''
                SELECT id FROM quiz_questions 
                WHERE language = ? AND difficulty = ? 
                ORDER BY created_at ASC LIMIT 1 OFFSET ?
            ''', (language, difficulty, question_index)).fetchone()

            if not question_id:
                return jsonify({'error': 'Question not found'}), 404

            # Update the question
            conn.execute('''
                UPDATE quiz_questions 
                SET question = ?, options = ?, answer = ?
                WHERE id = ?
            ''', (question, json.dumps(options), correct_answer, question_id['id']))
            conn.commit()

        # Reload quiz data from database
        load_quiz_data()

        return jsonify({
            'success': True,
            'message': 'Question updated successfully'
        }), 200

    except Exception as e:
        print(f"Error updating question: {e}")
        return jsonify({'error': 'Error updating question'}), 500

@app.route('/admin/delete_question/<language>/<difficulty>/<int:question_index>', methods=['POST'])
def delete_question(language, difficulty, question_index):
    """Delete a specific quiz question"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            # Get the question ID
            question_id = conn.execute('''
                SELECT id FROM quiz_questions 
                WHERE language = ? AND difficulty = ? 
                ORDER BY created_at ASC LIMIT 1 OFFSET ?
            ''', (language, difficulty, question_index)).fetchone()

            if not question_id:
                return jsonify({'error': 'Question not found'}), 404

            # Delete the question
            conn.execute('DELETE FROM quiz_questions WHERE id = ?', (question_id['id'],))
            conn.commit()

        # Reload quiz data from database
        load_quiz_data()

        return jsonify({
            'success': True,
            'message': 'Question deleted successfully'
        }), 200

    except Exception as e:
        print(f"Error deleting question: {e}")
        return jsonify({'error': 'Error deleting question'}), 500

@app.route('/admin_logout')
def admin_logout():
    """Logs out the admin"""
    session.pop('admin', None)
    session.pop('admin_id', None)
    flash("You have been logged out from the admin panel.", 'info')
    return redirect(url_for('admin_login'))

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    """
    Chatbot interface for language learning assistance.
    GET: Displays the chatbot interface
    POST: Handles chat messages and returns AI responses
    """
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get notification count for the navbar
    with get_db_connection() as conn:
        notification_count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (session['user_id'],)
        ).fetchone()[0]
    
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message', '')
        language = data.get('language', 'english')
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Create or update chat session
        with get_db_connection() as conn:
            if session_id:
                # Update existing session
                conn.execute('''
                    UPDATE chat_sessions 
                    SET last_message_at = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND user_id = ?
                ''', (session_id, session['user_id']))
            else:
                # Create new session
                session_id = f"sess-{secrets.token_hex(16)}"
                conn.execute('''
                    INSERT INTO chat_sessions (session_id, user_id, language)
                    VALUES (?, ?, ?)
                ''', (session_id, session['user_id'], language))

        # Create a more detailed prompt for better language learning interaction
        prompt = f"""You are a helpful and encouraging language tutor teaching {language}. 
        The student's message is: "{message}"
        
        Please respond in {language} and follow these guidelines:
        - If the student's message is in {language}, check for any grammar or vocabulary errors
        - If the student's message is in another language, help them express it in {language}
        - Keep responses friendly and educational
        - Include corrections when necessary
        - Provide encouragement
        
        Response:"""

        response_text = get_gemini_response(prompt)
        
        # Store the message and response
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO chat_messages (session_id, message, bot_response)
                VALUES (?, ?, ?)
            ''', (session_id, message, response_text))
            conn.commit()

        return jsonify({
            'response': response_text,
            'session_id': session_id
        }), 200
    
    return render_template('chatbot.html', 
                         username=session['username'],
                         notification_count=notification_count)

@app.route('/chat_history/sessions')
def get_chat_sessions():
    """
    Returns a list of chat sessions for the current user.
    """
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
    """
    Returns all messages for a specific chat session.
    """
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

# --- Achievement Definitions ---
ACHIEVEMENTS = {
    'hot_streak': {
        'name': 'Hot Streak',
        'description': '5 correct quizzes in a row',
        'check': lambda user_data: user_data['streak'] >= 5
    },
    'night_owl': {
        'name': 'Night Owl',
        'description': 'Complete a quiz after midnight',
        'check': lambda user_data, current_time: current_time.hour >= 0 and current_time.hour < 4
    },
    'early_bird': {
        'name': 'Early Bird',
        'description': 'Complete a quiz before 7am',
        'check': lambda user_data, current_time: current_time.hour >= 4 and current_time.hour < 7
    },
    'polyglot': {
        'name': 'Polyglot',
        'description': 'Complete quizzes in all available languages',
        'check': lambda user_data: len(user_data['completed_languages']) >= len(AVAILABLE_LANGUAGES)
    },
    'comeback_kid': {
        'name': 'Comeback Kid',
        'description': 'Get a perfect score after failing a quiz',
        'check': lambda user_data, last_quiz, current_quiz: 
            last_quiz and not last_quiz['passed'] and current_quiz['score'] == current_quiz['total']
    },
    'speed_demon': {
        'name': 'Speed Demon',
        'description': 'Finish a quiz in record time',
        'check': lambda user_data, quiz_time: quiz_time < 60  # Less than 60 seconds
    },
    'consistency_champ': {
        'name': 'Consistency Champ',
        'description': 'Complete quizzes 5 days in a row',
        'check': lambda user_data: user_data['daily_streak'] >= 5
    },
    'quick_thinker': {
        'name': 'Quick Thinker',
        'description': '5 questions correctly in under 10 seconds each',
        'check': lambda user_data, quick_answers: quick_answers >= 5
    },
    'basic_vocab': {
        'name': 'Basic Vocab',
        'description': 'Score 300 points in Beginner quizzes',
        'check': lambda user_data: user_data['beginner_points'] >= 300
    },
    'language_guru': {
        'name': 'Language Guru',
        'description': 'Having 5 streak',
        'check': lambda user_data: user_data['streak'] >= 5
    },
    'fluency_builder': {
        'name': 'Fluency Builder',
        'description': 'Complete 10 Advanced quizzes',
        'check': lambda user_data: user_data['advanced_quizzes_completed'] >= 10
    },
    'master_of_language': {
        'name': 'Master of Language',
        'description': 'Reach 1500 total points',
        'check': lambda user_data: user_data['total_points'] >= 1500
    }
}

def check_achievements(user_data, quiz_result=None):
    """
    Check and award achievements based on user data and quiz results
    
    Args:
        user_data (dict): User's progress and achievement data
        quiz_result (dict, optional): Results from the most recent quiz
        
    Returns:
        list: List of newly earned achievements
    """
    from datetime import datetime
    current_time = datetime.now()
    
    new_achievements = []
    
    for achievement_id, achievement in ACHIEVEMENTS.items():
        # Skip if already earned
        if achievement_id in user_data['badges']:
            continue
            
        # Prepare check parameters
        check_params = {'user_data': user_data}
        
        if quiz_result:
            check_params.update({
                'current_time': current_time,
                'last_quiz': user_data.get('last_quiz'),
                'current_quiz': quiz_result,
                'quiz_time': quiz_result.get('completion_time', float('inf')),
                'quick_answers': quiz_result.get('quick_answers', 0)
            })
        
        # Check if achievement is earned
        try:
            if achievement['check'](**{k: v for k, v in check_params.items() 
                                    if k in achievement['check'].__code__.co_varnames}):
                user_data['badges'].append(achievement_id)
                new_achievements.append(achievement_id)
        except Exception as e:
            print(f"Error checking achievement {achievement_id}: {str(e)}")
            
    return new_achievements

def load_quiz_data():
    """Load quiz questions from database into QUIZ_DATA dictionary"""
    global QUIZ_DATA
    QUIZ_DATA = {}
    
    with get_db_connection() as conn:
        questions = conn.execute('SELECT * FROM quiz_questions').fetchall()
        
        for q in questions:
            # Initialize language and difficulty if they don't exist
            if q['language'] not in QUIZ_DATA:
                QUIZ_DATA[q['language']] = {}
            if q['difficulty'] not in QUIZ_DATA[q['language']]:
                QUIZ_DATA[q['language']][q['difficulty']] = []
            
            # Add question to QUIZ_DATA
            QUIZ_DATA[q['language']][q['difficulty']].append({
                'question': q['question'],
                'type': q['question_type'],
                'options': json.loads(q['options']),
                'answer': q['answer'],
                'points': q['points']
            })

@app.route('/admin/import_questions', methods=['POST'])
def admin_import_questions():
    """Import questions from Excel file"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        # Check if file was uploaded
        if 'excel_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['excel_file']
        
        # Check if file is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Check file extension
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)'}), 400

        # Read Excel file
        import pandas as pd
        df = pd.read_excel(file)

        # Validate columns
        required_columns = ['Language', 'Difficulty', 'Question', 'Options', 'Correct Answer']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'Missing columns: {", ".join(missing_columns)}'}), 400

        # Connect to database
        with get_db_connection() as conn:
            success_count = 0
            error_count = 0

            # Process each row
            for index, row in df.iterrows():
                try:
                    # Validate difficulty
                    if row['Difficulty'].lower() not in ['beginner', 'intermediate', 'advanced']:
                        continue

                    # Process options - split by newline or semicolon
                    options = [opt.strip() for opt in str(row['Options']).replace('\n', ';').split(';') if opt.strip()]
                    
                    # Skip if less than 2 options
                    if len(options) < 2:
                        continue

                    # Skip if correct answer not in options
                    if str(row['Correct Answer']).strip() not in options:
                        continue

                    # Insert question into database
                    conn.execute('''
                        INSERT INTO quiz_questions 
                        (language, difficulty, question, options, answer)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        str(row['Language']).strip(),
                        str(row['Difficulty']).lower().strip(),
                        str(row['Question']).strip(),
                        json.dumps(options),
                        str(row['Correct Answer']).strip()
                    ))
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Error processing row {index + 2}: {str(e)}")

            conn.commit()

        # Reload quiz data
        load_quiz_data()

        # Return results
        if success_count > 0:
            message = f"Successfully imported {success_count} questions"
            if error_count > 0:
                message += f" ({error_count} failed)"
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({'error': 'No valid questions found in the file'}), 400

    except Exception as e:
        print(f"Error importing questions: {str(e)}")
        return jsonify({'error': f'Error importing questions: {str(e)}'}), 500

@app.route('/admin/delete_questions', methods=['POST'])
def admin_delete_questions():
    """Delete multiple questions at once"""
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        data = request.get_json()
        questions_to_delete = data.get('questions', [])
        
        if not questions_to_delete:
            return jsonify({'error': 'No questions specified'}), 400

        with get_db_connection() as conn:
            # Sort questions by index in descending order to avoid index shifting
            questions_to_delete.sort(key=lambda x: x['index'], reverse=True)
            
            for question in questions_to_delete:
                language = question['language']
                difficulty = question['difficulty']
                index = question['index']
                
                # Delete question from database
                conn.execute('''
                    DELETE FROM quiz_questions 
                    WHERE language = ? AND difficulty = ? 
                    AND id IN (
                        SELECT id FROM quiz_questions 
                        WHERE language = ? AND difficulty = ? 
                        LIMIT 1 OFFSET ?
                    )
                ''', (language, difficulty, language, difficulty, index))
            
            conn.commit()

        # Reload quiz data after deletion
        load_quiz_data()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"Error deleting questions: {str(e)}")
        return jsonify({'error': 'Failed to delete questions'}), 500

@app.route('/deactivate_account', methods=['POST'])
def deactivate_account():
    """
    Deactivates a user account (currently just logs out the user).
    In a production environment, this would set a flag in the database.
    """
    if 'username' not in session:
        return redirect(url_for('login'))
    # Here you can implement actual deactivation logic (e.g., set a flag in DB)
    # For now, just log the user out
    flash('Your account has been deactivated. You have been logged out.', 'info')
    session.clear()
    return redirect(url_for('login'))

@app.route('/close_account', methods=['POST'])
def close_account():
    """
    Permanently deletes a user account and all associated data.
    This includes quiz results, badges, notifications, chat history, etc.
    """
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_id = session['user_id']
    
    try:
        with get_db_connection() as conn:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Delete user's chat data
            # First get all session IDs
            session_ids = [row['session_id'] for row in 
                          conn.execute("SELECT session_id FROM chat_sessions WHERE user_id = ?", 
                                      (user_id,)).fetchall()]
            
            # Delete chat messages for those sessions
            for session_id in session_ids:
                conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            
            # Delete chat sessions
            conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
            
            # Delete other user data
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM quiz_results WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM quiz_results_enhanced WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
            
            # Finally delete the user
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            # Commit transaction
            conn.execute("COMMIT")
            
            flash('Your account has been permanently deleted. You may register a new account.', 'info')
            session.clear()
            return redirect(url_for('register'))
            
    except Exception as e:
        # Rollback transaction in case of error
        with get_db_connection() as conn:
            conn.execute("ROLLBACK")
        
        print(f"Error closing account: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        flash(f'Error closing account: {str(e)}', 'error')
        return redirect(url_for('settings'))

# --- Function to ensure database has required columns ---
def ensure_user_columns():
    """
    Ensures that the users table has all required columns.
    Adds new columns if they don't exist.
    """
    columns = [
        ('name', 'TEXT'),
        ('phone', 'TEXT'),
        ('location', 'TEXT'),
        ('website', 'TEXT'),
        ('avatar', 'TEXT'),
        ('timezone', 'TEXT'),
        ('datetime_format', 'TEXT')
    ]
    with get_db_connection() as conn:
        for col, typ in columns:
            try:
                conn.execute(f'ALTER TABLE users ADD COLUMN {col} {typ};')
            except Exception:
                pass  # Already exists
        conn.commit()

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles chat interactions with the AI language tutor.
    Stores conversation history in sessions and messages.
    """
    if 'username' not in session:
        return jsonify({'error': 'Please log in to use the chatbot'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        message = data.get('message', '').strip()
        language = data.get('language', 'english').strip()
        session_id = data.get('session_id')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Create or update chat session
        with get_db_connection() as conn:
            if session_id:
                # Update existing session
                conn.execute('''
                    UPDATE chat_sessions 
                    SET last_message_at = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND user_id = ?
                ''', (session_id, session['user_id']))
            else:
                # Create new session
                session_id = f"sess-{secrets.token_hex(16)}"
                conn.execute('''
                    INSERT INTO chat_sessions (session_id, user_id, language)
                    VALUES (?, ?, ?)
                ''', (session_id, session['user_id'], language))

        # Create a more detailed prompt for better language learning interaction
        prompt = f"""You are a helpful and encouraging language tutor teaching {language}. 
        The student's message is: "{message}"
        
        Please respond in {language} and follow these guidelines:
        - If the student's message is in {language}, check for any grammar or vocabulary errors
        - If the student's message is in another language, help them express it in {language}
        - Keep responses friendly and educational
        - Include corrections when necessary
        - Provide encouragement
        
        Response:"""

        response_text = get_gemini_response(prompt)
        
        # Store the message and response
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO chat_messages (session_id, message, bot_response)
                VALUES (?, ?, ?)
            ''', (session_id, message, response_text))
            conn.commit()

        return jsonify({
            'response': response_text,
            'session_id': session_id
        }), 200

    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'An error occurred processing your message'}), 500

if __name__ == '__main__':
    """
    Application entry point.
    Initializes the database, creates necessary directories, and starts the Flask server.
    """
    # Initialize the main database
    from scripts.init_db import initialize_database
    initialize_database()

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join('static', 'avatars'), exist_ok=True)
    
    # Copy default avatars if the avatars directory is empty
    avatars_dir = os.path.join('static', 'avatars')
    if os.path.exists(avatars_dir) and not os.listdir(avatars_dir):
        # Create some default avatars if they don't exist
        try:
            import shutil
            default_avatars_dir = os.path.join('static', 'images', 'default_avatars')
            if os.path.exists(default_avatars_dir):
                for avatar in os.listdir(default_avatars_dir):
                    if avatar.lower().endswith(('.png', '.jpg', '.jpeg')):
                        shutil.copy(
                            os.path.join(default_avatars_dir, avatar),
                            os.path.join(avatars_dir, avatar)
                        )
            else:
                # If no default avatars exist, create placeholder image
                print("No default avatars found. Avatar selection will be empty until you add some images.")
        except Exception as e:
            print(f"Warning: Could not copy default avatars: {str(e)}")

    # Make sure users table has all required columns
    ensure_user_columns()

    # Create chat history tables if they don't exist
    with get_db_connection() as conn:
        # Chat sessions table
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

        # Chat messages table
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
        conn.commit()

    # Load quiz data from database
    load_quiz_data()

    # Start the Flask application
    app.run(debug=True)