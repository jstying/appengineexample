"""
MIGRATION NOTE:
This application has been successfully migrated from Google Cloud NDB to Firebase Firestore.
The legacy App Engine ndb.Model configuration and context blocks have been replaced with the 
modern Firebase Admin SDK. The app.yaml configuration has also been upgraded to runtime: python312.
Note: Running this application locally requires a 'firebase-key.json' file. If you need step-by-step 
instructions on how to generate, download, and configure this key, please ask your AI assistant.
"""

from flask import Flask, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, firestore
import os
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        # First, try to fetch default credentials from the cloud environment (for App Engine deployment)
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    except Exception:
        # Fallback to local key file if cloud environment credentials are not found
        if os.path.exists('firebase-key.json'):
            cred = credentials.Certificate('firebase-key.json')
            firebase_admin.initialize_app(cred)
        else:
            raise RuntimeError("Failed to find valid Firebase credentials. Please check your local firebase-key.json file or cloud configuration.")

# Initialize Firestore client
db = firestore.client()

def get_user_by_username(username):
    """Fetch user data filtered by username"""
    users_ref = db.collection('users')
    query = users_ref.where('username', '==', username).limit(1).stream()
    for doc in query:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        return user_data
    return None

def get_user_by_email(email):
    """Fetch user data filtered by email"""
    users_ref = db.collection('users')
    query = users_ref.where('email', '==', email).limit(1).stream()
    for doc in query:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        return user_data
    return None

def create_user(username, email, password):
    """Create and store a new user document"""
    users_ref = db.collection('users')
    user_data = {
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password),
        'created_at': firestore.SERVER_TIMESTAMP 
    }
    _, doc_ref = users_ref.add(user_data)
    user_data['id'] = doc_ref.id
    return user_data

def get_user_by_id(user_id):
    """Fetch a single user document by its Firestore document ID"""
    doc_ref = db.collection('users').document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        return user_data
    return None

@app.route('/')
def home():
    """Render home page or dashboard based on session status"""
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user:
            return render_template('dashboard.html', user=user)
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        if get_user_by_username(username):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if get_user_by_email(email):
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        try:
            user = create_user(username, email, password)
            session['user_id'] = user['id']
            flash('Registration successful! Welcome!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user authentication login"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        user = get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Clear user session and log out"""
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    """Render profile details for authenticated users"""
    if 'user_id' not in session:
        flash('Please login to view your profile', 'error')
        return redirect(url_for('login'))
    
    # Fixed the function call bug from the previous block here
    user = get_user_by_id(session['user_id'])
    if not user:
        session.pop('user_id', None)
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)