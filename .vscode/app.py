from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
import os
from werkzeug.utils import secure_filename
import random
import sendgrid
from sendgrid.helpers.mail import Mail as SendGridMail
import logging  # Import the logging module
import json
from dotenv import load_dotenv
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# --- SendGrid Setup for 2FA ---
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'YOUR_SENDGRID_API_KEY')  # Get from environment variable or use placeholder
SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL', 'your-verified-sendgrid-email@example.com')  # Get from environment variable or use placeholder

# Initialize SendGrid client with error handling
try:
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
except Exception as e:
    logging.error(f"Failed to initialize SendGrid client: {e}")
    sg = None

# --- Flask-Mail Setup (for password reset - keep this) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('GMAIL_USERNAME')

# --- File Upload Setup ---
UPLOAD_FOLDER = 'static/uploads/'  # Folder where profile pictures will be saved
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

mail = Mail(app)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Database Functions ---
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    security_answer TEXT NOT NULL,
                    profile_picture TEXT
                )
            ''')
            conn.commit()
            logging.info("Database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Error initializing database: {e}")
        finally:
            conn.close()

def get_db_connection():
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def check_login(email, password, security_answer):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        user = conn.execute(
            "SELECT id, username, password, security_answer, email FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password) and user['security_answer'] == security_answer:
            return user
        return None
    except sqlite3.Error as e:
        logging.error(f"Database query error: {e}")
        return None
    finally:
        conn.close()

def register_user(username, email, password, security_answer):
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            return False
        hashed_password = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, email, password, security_answer) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, security_answer)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error during registration: {e}")
        return False
    finally:
        conn.close()

def generate_2fa_code():
    return random.randint(100000, 999999)

def send_2fa_email(user_email, code):
    if not sg:
        logging.error("SendGrid client not initialized")
        return False
        
    message = SendGridMail(
        from_email=SENDGRID_SENDER_EMAIL,
        to_emails=user_email,
        subject='Your 2FA Verification Code',
        plain_text_content=f'Your 2FA verification code is: {code}',
        html_content=f'Your 2FA verification code is: <strong>{code}</strong>'
    )
    try:
        response = sg.send(message)
        logging.info(f"2FA Email sent to {user_email}, status code: {response.status_code}")
        if response.status_code != 202:  # 202 is the accepted status code for SendGrid
            logging.warning(f"SendGrid response: {response.body}")  # Log the response body for more info
            return False
        return True
    except Exception as e:
        logging.error(f"Error sending 2FA email: {e}")
        return False

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        security_answer = request.form['security_answer']
        
        logging.info(f"Login attempt for email: {email}")
        
        user = check_login(email, password, security_answer)

        if user:
            logging.info(f"User {email} authenticated successfully")
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            
            # Generate and store 2FA code
            two_fa_code = generate_2fa_code()
            session['2fa_code'] = two_fa_code
            logging.info(f"Generated 2FA code for {email}: {two_fa_code}")
            
            # Send 2FA email
            if send_2fa_email(user['email'], two_fa_code):
                flash("✅ Verification code sent to your email. Please check your inbox and spam folder.")
                return redirect(url_for('verify_2fa'))
            else:
                flash("❌ Failed to send verification code. Please try again or contact support.")
                return redirect(url_for('login'))
        else:
            error = "❌ Invalid email, password, or security answer."
            logging.warning(f"Failed login attempt for {email}")
    
    return render_template('login.html', error=error)

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'user_id' not in session:
        flash('Please log in first.')
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST':
        entered_code = request.form['verification_code']
        stored_code = session.get('2fa_code')
        
        logging.info(f"2FA verification attempt for user: {session.get('email')}")

        if stored_code and str(entered_code) == str(stored_code):
            session['authenticated'] = True
            session.pop('2fa_code', None)
            flash("✅ Successfully verified!")
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Invalid verification code."
            
            # Resend new code
            new_code = generate_2fa_code()
            session['2fa_code'] = new_code
            if send_2fa_email(session['email'], new_code):
                flash("📧 A new verification code has been sent to your email.")
            else:
                flash("❌ Could not send new code. Please try again.")
    
    return render_template('verify_2fa.html', error=error)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.')
            return redirect(url_for('login'))
        try:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

            if user:
                reset_token = secrets.token_urlsafe(16)
                msg = Message('Password Reset Request', recipients=[email])
                msg.body = f"Click here to reset your password: http://localhost:5000/reset_password/{reset_token}"
                mail.send(msg)
                flash('Check your email for the password reset link.')
                return redirect(url_for('login'))
            else:
                error = "⚠ Email not found in our records."
        except sqlite3.Error as e:
            logging.error(f"Database error in forgot_password: {e}")
            flash('An error occurred. Please try again.')
        finally:
            conn.close()
    return render_template('forgot_password.html', error=error)

@app.route('/reset_password/<reset_token>', methods=['GET', 'POST'])
def reset_password(reset_token):
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)

        # In a real app, you'd need to link the reset token to a user and validate it
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.')
            return redirect(url_for('login'))
        try:
            conn.execute("UPDATE users SET password = ?", (hashed_password,))  # Simplified update - needs token verification
            conn.commit()
            flash("Your password has been successfully updated.")
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            logging.error(f"Database error in reset_password: {e}")
            flash('An error occurred. Please try again.')
        finally:
            conn.close()

    # If GET, render the password reset page
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
    if 'authenticated' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

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
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.')
            return redirect(url_for('admin_login'))
        try:
            users = conn.execute("SELECT id, username, email FROM users").fetchall()  # Show only relevant info
            return render_template('admin_dashboard.html', users=users)
        except sqlite3.Error as e:
            logging.error(f"Database error in admin_dashboard: {e}")
            flash('An error occurred.')
            return redirect(url_for('admin_login'))
        finally:
            conn.close()
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'admin' in session:
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.')
            return redirect(url_for('admin_dashboard'))
        try:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return redirect(url_for('admin_dashboard'))
        except sqlite3.Error as e:
            logging.error(f"Database error in delete_user: {e}")
            flash('An error occurred.')
            return redirect(url_for('admin_dashboard'))
        finally:
            conn.close()
    return redirect(url_for('admin_login'))

# --- Chatbot Route ---
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

# --- Progress Route ---
@app.route('/progress')
def progress():
    if 'username' in session:
        return render_template('progress.html', username=session['username'])
    return redirect(url_for('login'))

# --- Settings Route ---
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' in session:
        if request.method == 'POST':
            new_password = request.form['new_password']
            hashed_password = generate_password_hash(new_password)
            conn = get_db_connection()
            if conn is None:
                flash('Database connection error.')
                return redirect(url_for('settings'))
            try:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, session['username']))
                conn.commit()

                if 'profile_picture' in request.files:
                    file = request.files['profile_picture']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        session['profile_picture'] = filename
                return redirect(url_for('settings'))
            except sqlite3.Error as e:
                logging.error(f"Database error in settings: {e}")
                flash('An error occurred.')
                return redirect(url_for('settings'))
            finally:
                conn.close()
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.')
            return redirect(url_for('login'))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT profile_picture FROM users WHERE username = ?", (session.get('username'),))
            result = cursor.fetchone()
            profile_picture = result[0] if result else None
            return render_template('settings.html', username=session['username'], profile_picture=profile_picture)
        except sqlite3.Error as e:
            logging.error(f"Database error fetching profile picture: {e}")
            flash('An error occurred.')
            return redirect(url_for('login'))
        finally:
            conn.close()
    return redirect(url_for('login'))

# --- Dark Mode Toggle ---
@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    session['dark_mode'] = not session.get('dark_mode', False)
    return redirect(url_for('dashboard'))

# --- Profile Picture Upload Route ---
@app.route('/update_profile_picture', methods=['POST'])
def update_profile_picture():
    if 'profile_picture' not in request.files:
        flash("No file part")
        return redirect(request.url)
    file = request.files['profile_picture']
    if file.filename == '':
        flash("No selected file")
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash("Profile picture updated successfully!")
        return redirect(url_for('settings'))
    flash("Invalid file type. Only images are allowed.")
    return redirect(request.url)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    init_db()  # Initialize database on startup
    app.run(debug=True)