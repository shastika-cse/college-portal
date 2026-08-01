from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Users table with all fields (reg_no, class_name, section, year, semester)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            reg_no TEXT,
            class_name TEXT,
            section TEXT,
            year TEXT,
            semester TEXT
        )
    ''')
    # Assignments table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            target_class TEXT
        )
    ''')
    # Submissions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER,
            assignment_title TEXT,
            student_name TEXT,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            file_path TEXT,
            is_duplicate INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Home Route
@app.route('/')
def home():
    return render_template('index.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'faculty':
                return redirect(url_for('submissions'))
            else:
                return redirect(url_for('dashboard'))
        else:
            return "Invalid Credentials, please try again."
            
    return render_template('login.html')

# Register / Create Account Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        reg_no = request.form.get('reg_no', '')
        class_name = request.form.get('class_name', '')
        section = request.form.get('section', '')
        year = request.form.get('year', '')
        semester = request.form.get('semester', '')
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO users (username, email, password, role, reg_no, class_name, section, year, semester)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, password, role, reg_no, class_name, section, year, semester))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists!"
        conn.close()
        return redirect(url_for('login'))
        
    return render_template('register.html')

# Student Dashboard Route
@app.route('/dashboard')
@app.route('/student_dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
        
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
    progress_percentage = int((completed_count / len(assignments)) * 100) if assignments else 0
    
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

# All Assignments Route (Student View / Portal)
@app.route('/assignments')
def assignments():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    assignments = conn.execute("SELECT * FROM assignments").fetchall()
    conn.close()
    return render_template('assignments.html', assignments=assignments)

# Submit Assignment Route (Student)
@app.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session or session.get('role') != 'student':
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
            
            existing_sub = conn.execute(
                "SELECT * FROM submissions WHERE assignment_id = ? AND file_path = ? AND reg_no != ?",
                (assignment_id, file_path, user['reg_no'])
            ).fetchone()
            
            is_dup = 1 if existing_sub else 0
            
            conn.execute("""
                INSERT INTO submissions (assignment_id, assignment_title, student_name, reg_no, class_name, year, file_path, is_duplicate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (assignment_id, assignment['title'], user['username'], user['reg_no'], user['class_name'], user['year'], file_path, is_dup))
            conn.commit()
            
    conn.close()
    return redirect(url_for('assignments'))

# Faculty Submissions Route
@app.route('/submissions')
def submissions():
    if 'user_id' not in session or session.get('role') != 'faculty':
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
        
    submissions_list = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('submissions.html', submissions=submissions_list, assignments=assignments)

# Post Assignment Route (Faculty)
@app.route('/post_assignment', methods=['GET', 'POST'])
def post_assignment():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        target_class = request.form['target_class']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO assignments (title, description, deadline, target_class)
            VALUES (?, ?, ?, ?)
        ''', (title, description, deadline, target_class))
        conn.commit()
        conn.close()
        return redirect(url_for('submissions'))
        
    return render_template('post_assignment.html')

# Profile Route
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('student_profile.html', user=user)

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)