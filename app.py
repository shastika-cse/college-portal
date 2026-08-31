import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Change this to a secure random key

def get_db_connection():
    conn = sqlite3.connect('college_portal.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create tables if they do not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            reg_no TEXT,
            role TEXT DEFAULT 'student'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            designation TEXT,
            role TEXT DEFAULT 'faculty'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def resolve_display_name(user, username):
    if user and isinstance(user, sqlite3.Row):
        if 'name' in user.keys() and user['name']:
            return user['name']
    return username

@app.route('/')
def index():
    # Session-la user data iruntha, direct-ah dashboard-ku anuppiduvom
    if 'user_id' in session or 'username' in session:
        if session.get('role') == 'faculty':
            return redirect(url_for('submissions'))
        else:
            return redirect(url_for('student_dash'))
    
    # Session illa na mattum thaan login page-kku pogum
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Accept whichever field name the HTML form uses
        email = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name') or request.form.get('fullname') or email.split('@')[0]
        role = request.form.get('role', 'student').lower()
        reg_no = request.form.get('reg_no', '')

        print(f"DEBUG REGISTER -> Email: {email}, Password: {password}, Role: {role}")

        if not email or not password:
            return render_template('register.html', error="Email and Password are required!")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if role == 'faculty':
                cursor.execute(
                    "INSERT INTO faculty (username, email, password, name, designation, role) VALUES (?, ?, ?, ?, ?, ?)",
                    (email, email, password, name, 'Faculty', 'faculty')
                )
            else:
                cursor.execute(
                    "INSERT INTO students (username, email, password, name, reg_no, role) VALUES (?, ?, ?, ?, ?, ?)",
                    (email, email, password, name, reg_no, 'student')
                )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            print(f"Registration Error: {e}")
            return render_template('register.html', error=f"Error: {e}")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Grab input from whichever name the login form uses
        user_input = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        selected_role = request.form.get('role', 'student').lower()

        print(f"DEBUG LOGIN -> Input: {user_input}, Password: {password}, Role: {selected_role}")

        conn = get_db_connection()
        cursor = conn.cursor()
        user = None

        # Check in students and faculty tables
        cursor.execute("SELECT * FROM students WHERE (username = ? OR email = ?) AND password = ?", (user_input, user_input, password))
        user = cursor.fetchone()
        if user:
            selected_role = 'student'
        else:
            cursor.execute("SELECT * FROM faculty WHERE (username = ? OR email = ?) AND password = ?", (user_input, user_input, password))
            user = cursor.fetchone()
            if user:
                selected_role = 'faculty'

        if user:
            session['user_id'] = user['id'] if 'id' in user.keys() else user_input
            session['username'] = user['username'] if 'username' in user.keys() else user_input
            session['name'] = user['name'] if 'name' in user.keys() else user_input
            session['role'] = selected_role
            conn.close()

            if selected_role == 'faculty':
                return redirect(url_for('submissions'))
            else:
                return redirect(url_for('student_dash'))
        else:
            conn.close()
            error = "Invalid Email/Username or Password! Please check."

    return render_template('login.html', error=error)

@app.route('/student_dash')
def student_dash():
    if 'username' not in session and 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE username = ? OR email = ?", (session.get('username'), session.get('username')))
    student = cursor.fetchone()
    conn.close()

    return render_template('student_dashboard.html', student=student)

@app.route('/submissions')
def submissions():
    if 'username' not in session and 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faculty WHERE username = ? OR email = ?", (session.get('username'), session.get('username')))
    faculty = cursor.fetchone()
    conn.close()

    return render_template('faculty_profile.html', faculty=faculty)

@app.route('/profile')
def profile():
    if 'username' not in session and 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session.get('role') == 'faculty':
        cursor.execute("SELECT * FROM faculty WHERE username = ? OR email = ?", (session.get('username'), session.get('username')))
        user = cursor.fetchone()
        conn.close()
        return render_template('faculty_profile.html', faculty=user)
    else:
        cursor.execute("SELECT * FROM students WHERE username = ? OR email = ?", (session.get('username'), session.get('username')))
        user = cursor.fetchone()
        conn.close()
        return render_template('student_profile.html', student=user)
    
@app.route('/edit_faculty_profile', methods=['GET', 'POST'])
def edit_faculty_profile():
    if 'username' not in session and 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Print form data to terminal to see what's coming from HTML
        print("FORM DATA RECEIVED:", request.form)
        
        name = request.form.get('name') or request.form.get('fullname') or request.form.get('username')
        designation = request.form.get('designation')
        department = request.form.get('department')
        phone = request.form.get('phone') or request.form.get('phone_number')
        room = request.form.get('room') or request.form.get('office_room_number')
        
        username_key = session.get('username')
        
        try:
            # Update basic fields that definitely exist in table
            cursor.execute(
                "UPDATE faculty SET name = ?, designation = ? WHERE username = ? OR email = ?",
                (name, designation, username_key, username_key)
            )
            conn.commit()
            print("Database update successful!")
        except Exception as e:
            print(f"Update Error: {e}")
            
        conn.close()
        return redirect(url_for('profile'))
        
    cursor.execute("SELECT * FROM faculty WHERE username = ? OR email = ?", (session.get('username'), session.get('username')))
    faculty = cursor.fetchone()
    conn.close()
    return render_template('edit_faculty_profile.html', faculty=faculty)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)