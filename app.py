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
smtp_port = 587  # TLS port for Gmail
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
    'beginner': {'points': 200, 'badges': ['basic_vocab', 'simple_sentences']},
    'intermediate': {'points': 500, 'badges': ['grammar_fundamentals', 'common_phrases']},
    'advanced': {'points': 1000, 'badges': ['complex_grammar', 'idioms']},
    'fluent': {'points': 2000, 'badges': ['mastery']}
}

# --- Points System Configuration ---
# These settings control how points are awarded during quizzes
POINTS_PER_CORRECT_ANSWER = 10  # Base points for each correct answer
STREAK_BONUS = 5                # Additional points for consecutive correct answers
TIME_BONUS_MULTIPLIER = 0.2     # Percentage bonus for quick answers (20% of base points)
MIN_TIME_FOR_BONUS = 10         # Maximum seconds to qualify for time bonus

# --- Database Functions ---
# These functions handle database connections and common database operations

def get_db_connection():
    """
    Creates and returns a connection to the SQLite database with proper configuration.

    Returns:
        sqlite3.Connection: A configured database connection
    """
    conn = sqlite3.connect('database.db')
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
            'POINTS_PER_CORRECT_ANSWER': POINTS_PER_CORRECT_ANSWER,
            'STREAK_BONUS': STREAK_BONUS,
            'TIME_BONUS_MULTIPLIER': TIME_BONUS_MULTIPLIER
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
            'advanced': {'points_earned': 0, 'quizzes': 0},
            'fluent': {'points_earned': 0, 'quizzes': 0}
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
    # Fluent level (highest)
    if total_points >= LEVEL_REQUIREMENTS['fluent']['points']:
        data['current_level'] = 'fluent'
        data['next_level'] = None
        data['points_to_next'] = 0
        data['level_complete'] = True

        # Distribute points across levels for display
        data['levels']['beginner']['points_earned'] = LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['intermediate']['points_earned'] = LEVEL_REQUIREMENTS['intermediate']['points'] - LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['advanced']['points_earned'] = LEVEL_REQUIREMENTS['advanced']['points'] - LEVEL_REQUIREMENTS['intermediate']['points']
        data['levels']['fluent']['points_earned'] = total_points - LEVEL_REQUIREMENTS['advanced']['points']

    # Advanced level
    elif total_points >= LEVEL_REQUIREMENTS['advanced']['points']:
        data['current_level'] = 'advanced'
        data['next_level'] = 'fluent'
        data['points_to_next'] = max(0, LEVEL_REQUIREMENTS['fluent']['points'] - total_points)
        data['level_complete'] = False

        # Distribute points across levels
        data['levels']['beginner']['points_earned'] = LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['intermediate']['points_earned'] = LEVEL_REQUIREMENTS['intermediate']['points'] - LEVEL_REQUIREMENTS['beginner']['points']
        data['levels']['advanced']['points_earned'] = total_points - LEVEL_REQUIREMENTS['intermediate']['points']
        data['levels']['fluent']['points_earned'] = 0

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
        data['levels']['fluent']['points_earned'] = 0

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
        data['levels']['fluent']['points_earned'] = 0

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

    # Mastery badge (fluent level)
    if total_points >= LEVEL_REQUIREMENTS['fluent']['points']:
        data['badges'].append('mastery')

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
            # Connect to the SMTP server
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()  # Identify yourself to the server

            # Enable TLS encryption
            server.starttls()
            server.ehlo()  # Re-identify yourself over TLS connection

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
from quiz_data import QUIZ_DATA  # Pre-defined quiz questions by language and difficulty

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
    Allows users to change their email, password, bio, and profile picture.
    """
    # Ensure user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get current user data
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (session['username'],)).fetchone()

    # Handle form submission for profile updates
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        bio = request.form.get('bio')
        new_password = request.form.get('new_password')
        urls = request.form.get('urls')

        # Handle profile picture upload
        profile_pic_filename = None
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
            update_data = {
                'email': email,
                'bio': bio,
                'urls': urls
            }

            # Add password if it's being changed
            if new_password:
                update_data['password'] = generate_password_hash(new_password)

            # Add profile picture if it was uploaded
            if profile_pic_filename:
                update_data['profile_picture'] = profile_pic_filename

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

            # Update session if profile picture was changed
            if profile_pic_filename:
                session['profile_picture'] = profile_pic_filename

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('settings'))

        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')

    # Display settings form with current user data
    return render_template('settings.html',
                         username=session['username'],
                         user=user)

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
            (user_id,)  # Limit to 20 read notifications to avoid performance issues
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
            options = q['options']
            if q.get('shuffle_options', True):
                options = sample(options, len(options))
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
    base_points = score * POINTS_PER_CORRECT_ANSWER
    streak_bonus = (max_streak // 3) * STREAK_BONUS  # Bonus every 3 correct in a row
    time_bonus = 0

    # Time bonus for quick answers
    avg_time = total_time / total_questions if total_questions > 0 else 0
    if avg_time < MIN_TIME_FOR_BONUS:
        time_bonus = base_points * TIME_BONUS_MULTIPLIER * (1 - (avg_time / MIN_TIME_FOR_BONUS))

    points_earned = int(base_points + streak_bonus + time_bonus)

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
            elif (total_points_before < LEVEL_REQUIREMENTS['fluent']['points'] and
                  current_total_points >= LEVEL_REQUIREMENTS['fluent']['points']):
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

        # In a production environment, replace this with proper authentication
        # using database-stored credentials and password hashing
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')

        if email == admin_email and password == admin_password:
            session['admin'] = True
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

    return render_template('admin_dashboard.html', users=users)

@app.route('/admin_logout')
def admin_logout():
    """
    Logs out the admin by removing the admin session variable.
    """
    session.pop('admin', None)
    flash("You have been logged out from the admin panel.", 'info')
    return redirect(url_for('admin_login'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """
    Deletes a user from the database.
    Only accessible to authenticated admins.

    Args:
        user_id (int): The ID of the user to delete
    """
    if 'admin' not in session:
        flash("You must be logged in as an admin to delete users.", 'error')
        return redirect(url_for('admin_login'))

    # Delete the user from the database
    with get_db_connection() as conn:
        # First check if the user exists
        user = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()

        if user:
            # Delete the user
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash(f"User {user['username']} has been deleted.", 'success')
        else:
            flash("User not found.", 'error')

    return redirect(url_for('admin_dashboard'))

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
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        prompt = f"""You are a language learning chatbot. Respond to the user in {language}. Keep responses concise.
User: {message}
Chatbot: """
        response_text = get_gemini_response(prompt)
        return jsonify({'response': response_text}), 200
    
    return render_template('chatbot.html', 
                         username=session['username'],
                         notification_count=notification_count)

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

if __name__ == '__main__':
    """
    Application entry point.
    Initializes the database, creates necessary directories, and starts the Flask server.
    """
    # Initialize the main database
    from init_db import initialize_database
    initialize_database()

    # Ensure upload folder exists for profile pictures and other uploads
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Create database tables if they don't exist
    with get_db_connection() as conn:
        # Users table - stores user account information
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,              -- Stored as a hash
                security_answer TEXT NOT NULL,       -- For account recovery
                is_admin INTEGER DEFAULT 0,          -- Admin flag
                reset_token TEXT,                    -- For password reset
                bio TEXT,                            -- User profile bio
                urls TEXT,                           -- Social media links
                profile_picture TEXT,                -- Profile picture filename
                dark_mode INTEGER DEFAULT 0          -- UI preference
            )
        ''')

        # Quiz results table - stores detailed quiz results
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_results_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,              -- Quiz language
                difficulty TEXT NOT NULL,            -- Quiz difficulty level
                score INTEGER NOT NULL,              -- Number of correct answers
                total INTEGER NOT NULL,              -- Total number of questions
                percentage REAL NOT NULL,            -- Score percentage
                passed INTEGER DEFAULT 0,            -- Whether the quiz was passed (≥80%)
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                question_details TEXT NOT NULL,      -- JSON with detailed question data
                points_earned INTEGER DEFAULT 0,     -- Points earned from this quiz
                streak_bonus INTEGER DEFAULT 0,      -- Bonus points from streaks
                time_bonus INTEGER DEFAULT 0,        -- Bonus points from fast answers
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # User badges table - tracks achievements
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,              -- Language the badge was earned in
                badge_id TEXT NOT NULL,              -- Badge identifier
                earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, language, badge_id)  -- Prevent duplicate badges
            )
        ''')

        # Notifications table - stores user notifications
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,               -- Notification message
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,           -- Whether notification has been read
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()

    # Start the Flask application
    # In production, you would use a proper WSGI server like Gunicorn
    app.run(debug=True)