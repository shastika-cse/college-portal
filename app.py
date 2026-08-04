import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def init_db(conn=None):
    own_connection = conn is None
    if conn is None:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row

    conn.executescript('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            deadline TEXT,
            target_class TEXT
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            full_name TEXT,
            employee_id TEXT,
            designation TEXT,
            department TEXT,
            email TEXT,
            phone TEXT,
            office_room TEXT,
            qualification TEXT,
            specialization TEXT,
            experience TEXT,
            subjects_handling TEXT,
            current_subjects TEXT,
            research_areas TEXT,
            bio TEXT,
            philosophy TEXT
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            full_name TEXT,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            password TEXT
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_title TEXT,
            student_name TEXT,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            file_path TEXT,
            timestamp TEXT,
            is_duplicate INTEGER DEFAULT 0
        );
    ''')
    conn.commit()

    if own_connection:
        conn.close()


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'faculty')

        conn = get_db_connection()
        cursor = conn.cursor()
        user = None
        name = username

        if role == 'faculty':
            cursor.execute("SELECT * FROM faculty WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                name = user['full_name'] or user['username'] or username
        else:
            cursor.execute("SELECT * FROM students WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                name = user['full_name'] or user['username'] or username

        conn.close()

        session['user_id'] = user['id'] if user and 'id' in user.keys() else 1
        session['username'] = username
        session['name'] = name or username
        session['role'] = role

        if role == 'faculty':
            return redirect(url_for('submissions'))
        else:
            return redirect(url_for('assignments_list'))

    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

    return render_template(
        'submissions.html',
        submissions=submissions_list,
        assignments=assignments,
        display_name=session.get('name') or session.get('username') or 'Faculty'
    )

@app.route('/faculty_profile')
def faculty_profile():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faculty WHERE username = ?", (session.get('username'),))
    faculty = cursor.fetchone()
    conn.close()
    
    return render_template('faculty_profile.html', faculty=faculty)

@app.route('/edit_faculty_profile', methods=['GET', 'POST'])
def edit_faculty_profile():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        employee_id = request.form.get('employee_id')
        designation = request.form.get('designation')
        department = request.form.get('department')
        email = request.form.get('email')
        phone = request.form.get('phone')
        office_room = request.form.get('office_room')
        qualification = request.form.get('qualification')
        specialization = request.form.get('specialization')
        experience = request.form.get('experience')
        subjects_handling = request.form.get('subjects_handling')
        current_subjects = request.form.get('current_subjects')
        research_areas = request.form.get('research_areas')
        bio = request.form.get('bio')
        philosophy = request.form.get('philosophy')
        
        cursor.execute("SELECT * FROM faculty WHERE username = ?", (session.get('username'),))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE faculty SET full_name=?, employee_id=?, designation=?, department=?, email=?, 
                phone=?, office_room=?, qualification=?, specialization=?, experience=?, 
                subjects_handling=?, current_subjects=?, research_areas=?, bio=?, philosophy=? 
                WHERE username=?
            ''', (full_name, employee_id, designation, department, email, phone, office_room, 
                  qualification, specialization, experience, subjects_handling, current_subjects, 
                  research_areas, bio, philosophy, session.get('username')))
        else:
            cursor.execute('''
                INSERT INTO faculty (username, full_name, employee_id, designation, department, email, 
                phone, office_room, qualification, specialization, experience, subjects_handling, 
                current_subjects, research_areas, bio, philosophy) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (session.get('username'), full_name, employee_id, designation, department, email, 
                  phone, office_room, qualification, specialization, experience, subjects_handling, 
                  current_subjects, research_areas, bio, philosophy))
        
        conn.commit()
        conn.close()
        return redirect(url_for('faculty_profile'))
        
    # GET method part (Outside POST block)
    cursor.execute("SELECT * FROM faculty WHERE username = ?", (session.get('username'),))
    faculty = cursor.fetchone()
    conn.close()
    
    return render_template('edit_faculty_profile.html', faculty=faculty)

@app.route('/post_assignment', methods=['GET', 'POST'])
def post_assignment():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline = request.form.get('deadline')
        target_class = request.form.get('target_class')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO assignments (title, description, deadline, target_class) VALUES (?, ?, ?, ?)',
                     (title, description, deadline, target_class))
        conn.commit()
        conn.close()
        return redirect(url_for('submissions'))
        
    return render_template('post_assignment.html')

@app.route('/assignments')
def assignments_list():
    conn = get_db_connection()
    assignments_list = conn.execute('SELECT * FROM assignments').fetchall()
    conn.close()
    return render_template('assignments.html', assignments=assignments_list)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Registration logic inga varum (if needed)
        return redirect(url_for('login'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)