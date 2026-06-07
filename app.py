from flask import Flask, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import ndb
import os
import secrets


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Initialize NDB client
ndb_client = ndb.Client()

# Main Class
class User(ndb.Model):
    """User model for storing user credentials"""
    username = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    password_hash = ndb.StringProperty(required=True)
    created_at = ndb.DateTimeProperty(auto_now_add=True)

def get_user_by_username(username):
    """Get user by username"""
    with ndb_client.context():
        return User.query(User.username == username).get()

def get_user_by_email(email):
    """Get user by email"""
    with ndb_client.context():
        return User.query(User.email == email).get()

def create_user(username, email, password):
    """Create new user"""
    with ndb_client.context():
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        user.put()
        return user

@app.route('/')
def home():
    """Home page"""
    if 'user_id' in session:
        with ndb_client.context():
            user = User.get_by_id(session['user_id'])
            return render_template('dashboard.html', user=user)
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if get_user_by_username(username):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if get_user_by_email(email):
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create user
        try:
            user = create_user(username, email, password)
            session['user_id'] = user.key.id()
            flash('Registration successful! Welcome!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        user = get_user_by_username(username)
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.key.id()
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    """User profile page"""
    if 'user_id' not in session:
        flash('Please login to view your profile', 'error')
        return redirect(url_for('login'))
    
    with ndb_client.context():
        user = User.get_by_id(session['user_id'])
        if not user:
            session.pop('user_id', None)
            flash('User not found', 'error')
            return redirect(url_for('login'))
        
        return render_template('profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)
