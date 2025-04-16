<<<<<<< HEAD
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
=======
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Initialize the Flask app
app = Flask(__name__)

# Secret key for session management
app.config['SECRET_KEY'] = 'your_secret_key'

# Database configuration (SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable track modifications to avoid warning

# Initialize the database, bcrypt for password hashing, and login manager for session management
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to login page if not logged in

# User model (with UserMixin for Flask-Login functionality)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Create database tables (if they don't exist)
with app.app_context():
    db.create_all()

# Flask-Login user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for Registration (User Sign Up)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if the user already exists in the database
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        # Create new user and add to the database
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))  # Redirect to login after registration

    return render_template('register.html')

# Route for Login (User Sign In)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        email = request.form['email']
        password = request.form['password']

        # Check if the user exists in the database
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            # Log in the user
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to dashboard

        flash('Login Unsuccessful. Please check email and password.', 'danger')

    return render_template('login.html')

# Route for Dashboard (Accessible only after login)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)

# Route for Logout (Log out the user and redirect to login page)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
>>>>>>> bb5bf159250cc7f755d0ace9965129a5317ab9fd
