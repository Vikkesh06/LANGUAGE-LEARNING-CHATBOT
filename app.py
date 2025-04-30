from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
import os
from werkzeug.utils import secure_filename
import random

<<<<<<< HEAD
app = Flask(__name__)  # Change here
=======
app = Flask(_name_)  
>>>>>>> main
app.secret_key = 'supersecretkey'  # Needed for session handling

# --- Flask-Mail Setup ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Your email address
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# --- File Upload Setup ---
UPLOAD_FOLDER = 'static/uploads/'  # Folder where profile pictures will be saved
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

mail = Mail(app)

# --- Database Functions ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        user = check_login(email, password, security_answer)
        
        if user:
            session['username'] = user['username']
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Invalid email, password, or security answer."
    return render_template('login.html', error=error)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        with get_db_connection() as conn:
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
    return render_template('forgot_password.html', error=error)

@app.route('/reset_password/<reset_token>', methods=['GET', 'POST'])
def reset_password(reset_token):
    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)

        # Update the password in the database for the user with the corresponding reset token
        with get_db_connection() as conn:
            conn.execute("UPDATE users SET password = ? WHERE reset_token = ?", (hashed_password, reset_token))
            conn.commit()

        flash("Your password has been successfully updated.")
        return redirect(url_for('login'))

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
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('email', None)
    return redirect(url_for('login'))

<<<<<<< HEAD

# --- Admin Routes --- 
=======
# --- Admin Routes ---
>>>>>>> main
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

<<<<<<< HEAD
# --- Chatbot Route --- 
=======
# --- Chatbot Route ---
>>>>>>> main
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'username' in session:
        if request.method == 'POST':
            user_message = request.form['user_message']
            
            # Handle user input and generate a response
            bot_response = handle_chatbot_response(user_message)
            return jsonify({'bot_response': bot_response})
        return render_template('chatbot.html', username=session['username'])
    return redirect(url_for('login'))

def handle_chatbot_response(user_message):
    # Example of a language learning chatbot response
    if user_message.lower() in ["hello", "hi", "hey"]:
        return "Hello! How can I help you with your language learning today?"
    elif user_message.lower() == "grammar tip":
        return "In Spanish, adjectives usually come after the noun."
    else:
        return "I'm here to help with vocabulary and grammar tips. Ask me anything!"

<<<<<<< HEAD
# --- Progress Route --- 
=======
# --- Progress Route ---
>>>>>>> main
@app.route('/progress')
def progress():
    if 'username' in session:
        return render_template('progress.html', username=session['username'])
    return redirect(url_for('login'))

<<<<<<< HEAD
# --- Settings Route --- 
=======
# --- Settings Route ---
>>>>>>> main
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' in session:
        if request.method == 'POST':
            # Handle password update
            new_password = request.form['new_password']
<<<<<<< HEAD
            if new_password:
                hashed_password = generate_password_hash(new_password)
                with get_db_connection() as conn:
                    conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, session['username']))
                    conn.commit()

            # Handle bio update
            new_bio = request.form['bio']
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET bio = ? WHERE username = ?", (new_bio, session['username']))
                conn.commit()
            session['bio'] = new_bio  # Save the bio in session for immediate use

            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    session['profile_picture'] = filename  # Store the image name in the session

            return redirect(url_for('dashboard'))

        # Fetch current bio from the database
        with get_db_connection() as conn:
            user = conn.execute("SELECT bio FROM users WHERE username = ?", (session['username'],)).fetchone()
            bio = user['bio'] if user else ''  # Get the bio from the database

        return render_template('settings.html', username=session['username'], bio=bio)

    return redirect(url_for('login'))
    

=======
            hashed_password = generate_password_hash(new_password)
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, session['username']))
                conn.commit()

            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    session['profile_picture'] = filename  # Store the image name in the session

            return redirect(url_for('dashboard'))
        return render_template('settings.html', username=session['username'])
    return redirect(url_for('login'))

>>>>>>> main
# --- Dark Mode Toggle --- 
@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    if 'dark_mode' in session:
        session.pop('dark_mode')
    else:
        session['dark_mode'] = True
    return redirect(url_for('dashboard'))

<<<<<<< HEAD
# --- Profile Picture Upload Route --- 
=======
# --- Profile Picture Upload Route ---
>>>>>>> main
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

<<<<<<< HEAD
# Helper function to check allowed file types
=======
>>>>>>> main
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

<<<<<<< HEAD
if __name__ == '__main__':
    app.run(debug=True)  # Change here
=======
if _name_ == '_main_':
    app.run(debug=True)
>>>>>>> main
