from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import date

app = Flask(__name__)
app.secret_key = 'super_secret_key_college_portal'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['DATABASE'] = os.path.join(BASE_DIR, 'college_portal.db')

# Database Connection Setup
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Create Tables if not exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            phone TEXT,
            department TEXT,
            profile_updated_at TEXT
        )
    ''')
    
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for column_name, column_definition in [
        ('phone', 'TEXT'),
        ('department', 'TEXT'),
        ('profile_updated_at', 'TEXT')
    ]:
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            target_class TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            assignment_title TEXT,
            student_name TEXT,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            file_path TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
# Home Route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dashboard')
@app.route('/student_dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('assignments'))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    student_class = student['class_name'] if student and student['class_name'] else ''

    assignments = conn.execute(
        "SELECT * FROM assignments WHERE target_class = 'All' OR target_class = ?",
        (student_class,)
    ).fetchall()

    submitted_assignment_ids = {
        row['assignment_id']
        for row in conn.execute(
            "SELECT assignment_id FROM submissions WHERE reg_no = ? AND class_name = ?",
            (student['reg_no'] if student else '', student_class)
        ).fetchall()
        if row['assignment_id'] is not None
    }

    today = date.today().isoformat()
    submitted_count = len(submitted_assignment_ids)
    completed_count = 0
    for assignment in assignments:
        if assignment['id'] in submitted_assignment_ids:
            if assignment['deadline'] and assignment['deadline'] <= today:
                completed_count += 1
    pending_count = len(assignments) - submitted_count
    progress_percentage = int((completed_count / len(assignments) * 100)) if assignments else 0

    conn.close()
    return render_template(
        'student_dashboard.html',
        student=student,
        assignments=assignments,
        submitted_count=submitted_count,
        completed_count=completed_count,
        pending_count=pending_count,
        progress_percentage=progress_percentage
    )

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('assignments'))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    error = None
    success = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        reg_no = request.form.get('reg_no', '').strip()
        class_name = request.form.get('class_name', '').strip()
        year = request.form.get('year', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()

        if not username or not email:
            error = 'Name and email are required.'
        else:
            existing_user = conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?',
                (email, session['user_id'])
            ).fetchone()
            if existing_user:
                error = 'That email is already in use by another account.'
            else:
                conn.execute(
                    '''
                    UPDATE users
                    SET username = ?, email = ?, reg_no = ?, class_name = ?, year = ?, phone = ?, department = ?, profile_updated_at = ?
                    WHERE id = ?
                    ''',
                    (username, email, reg_no, class_name, year, phone, department, date.today().isoformat(), session['user_id'])
                )
                conn.commit()
                session['username'] = username
                session['class_name'] = class_name
                session['year'] = year
                session['reg_no'] = reg_no
                success = 'Your profile was updated successfully.'
                student = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    conn.close()
    return render_template('student_profile.html', student=student, error=error, success=success)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('assignments'))

    conn = get_db_connection()
    student = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    error = None
    success = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        reg_no = request.form.get('reg_no', '').strip()
        class_name = request.form.get('class_name', '').strip()
        year = request.form.get('year', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()

        if not username or not email:
            error = 'Name and email are required.'
        else:
            existing_user = conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?',
                (email, session['user_id'])
            ).fetchone()
            if existing_user:
                error = 'That email is already in use by another account.'
            else:
                conn.execute(
                    '''
                    UPDATE users
                    SET username = ?, email = ?, reg_no = ?, class_name = ?, year = ?, phone = ?, department = ?, profile_updated_at = ?
                    WHERE id = ?
                    ''',
                    (username, email, reg_no, class_name, year, phone, department, date.today().isoformat(), session['user_id'])
                )
                conn.commit()
                session['username'] = username
                session['class_name'] = class_name
                session['year'] = year
                session['reg_no'] = reg_no
                success = 'Your profile was updated successfully.'
                student = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

    conn.close()
    return render_template('student_profile.html', student=student, error=error, success=success)

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        reg_no = request.form.get('reg_no', '')
        class_name = request.form.get('class_name', '')
        year = request.form.get('year', '')
        
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO users (username, email, password, role, reg_no, class_name, year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (username, email, password, role, reg_no, class_name, year))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Email already exists! Please login."
            
    return render_template('register.html')
# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['class_name'] = user['class_name'] or ''
            session['year'] = user['year'] or ''
            session['reg_no'] = user['reg_no'] or ''
            if user['role'] == 'student':
                return redirect(url_for('dashboard'))
            return redirect(url_for('assignments'))
        else:
            error = "Invalid Credentials! Please check your email and password."
            
    return render_template('login.html', error=error)

# Assignments Main Page (List assignments)
@app.route('/assignments')
def assignments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # If user is student, filter assignments based on their class or 'All'
    if session['role'] == 'student':
        student_class = session.get('class_name', '')
        assignments = conn.execute(
            "SELECT * FROM assignments WHERE target_class = 'All' OR target_class = ?", 
            (student_class,)
        ).fetchall()
    else:
        # Faculty can see all assignments they posted
        assignments = conn.execute("SELECT * FROM assignments").fetchall()
        
    conn.close()
    return render_template('assignments.html', assignments=assignments)

# Faculty: Post Assignment Page
@app.route('/post_assignment', methods=['GET', 'POST'])
def post_assignment():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        target_class = request.form['target_class']
        
        conn = get_db_connection()
        conn.execute("INSERT INTO assignments (title, description, deadline, target_class) VALUES (?, ?, ?, ?)",
                     (title, description, deadline, target_class))
        conn.commit()
        conn.close()
        return redirect(url_for('assignments'))
        
    return render_template('post_assignment.html')

@app.route('/submissions')
def submissions():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
        
    filter_assignment = request.args.get('filter_assignment', '')
    filter_reg = request.args.get('filter_reg', '')
    filter_class = request.args.get('filter_class', '')
    filter_year = request.args.get('filter_year', '')
    
    conn = get_db_connection()
    assignments = conn.execute("SELECT * FROM assignments").fetchall()
    
    query = "SELECT * FROM submissions WHERE 1=1"
    params = []
    
    if filter_assignment:
        query += " AND assignment_title = ?"
        params.append(filter_assignment)
    if filter_reg:
        query += " AND reg_no LIKE ?"
        params.append(f"%{filter_reg}%")
    if filter_class:
        query += " AND class_name LIKE ?"
        params.append(f"%{filter_class}%")
    if filter_year:
        query += " AND year LIKE ?"
        params.append(f"%{filter_year}%")
        
    submissions = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('submissions.html', submissions=submissions, assignments=assignments)
# Student: Submit Assignment Page
@app.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            os.makedirs('static/uploads', exist_ok=True)
            file_path = os.path.join('static/uploads', file.filename)
            file.save(file_path)
            
            conn.execute("""
                INSERT INTO submissions (assignment_id, assignment_title, student_name, reg_no, class_name, year, file_path) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (assignment_id, assignment['title'], user['username'], user['reg_no'], user['class_name'], user['year'], file_path))
            conn.commit()
            
    conn.close()
    return redirect(url_for('assignments'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)