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
            philosophy TEXT,
            role TEXT DEFAULT 'faculty'
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            full_name TEXT,
            reg_no TEXT,
            class_name TEXT,
            year TEXT,
            password TEXT,
            role TEXT DEFAULT 'student'
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

    for table_name, default_role in (('faculty', 'faculty'), ('students', 'student')):
        columns = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        has_role = any(column['name'] == 'role' for column in columns)
        if not has_role:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN role TEXT DEFAULT '{default_role}'")

    conn.commit()

    if own_connection:
        conn.close()


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def resolve_display_name(user, fallback_username):
    if user is None:
        return fallback_username

    if isinstance(user, sqlite3.Row):
        for key in ('full_name', 'name', 'username'):
            if key in user.keys() and user[key]:
                return user[key]
        return fallback_username

    if isinstance(user, dict):
        for key in ('full_name', 'name', 'username'):
            value = user.get(key)
            if value:
                return value
        return fallback_username

    if isinstance(user, tuple):
        for index in (2, 1, 0):
            if len(user) > index and user[index]:
                return user[index]
        return fallback_username

    return fallback_username


def row_to_dict(row):
    if row is None:
        return {}
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    if isinstance(row, dict):
        return row
    return {}


init_db()

@app.route('/')
def index():
    user_id = session.get('user_id')
    username = session.get('username')
    role = session.get('role')

    if user_id or username:
        if role == 'student':
            return redirect(url_for('dashboard'))
        return redirect(url_for('submissions'))

    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        selected_role = request.form.get('role', 'faculty')

        conn = get_db_connection()
        cursor = conn.cursor()
        user = None

        if selected_role == 'faculty':
            cursor.execute("SELECT * FROM faculty WHERE username = ?", (username,))
            user = cursor.fetchone()
        else:
            cursor.execute("SELECT * FROM students WHERE username = ?", (username,))
            user = cursor.fetchone()

        name = resolve_display_name(user, username)
        db_username = username
        if user and isinstance(user, sqlite3.Row):
            if 'username' in user.keys() and user['username']:
                db_username = user['username']

        role_from_db = selected_role
        if user and isinstance(user, sqlite3.Row):
            if 'role' in user.keys() and user['role']:
                role_from_db = user['role']
            elif 'designation' in user.keys() and user['designation']:
                role_from_db = 'faculty'
            elif 'reg_no' in user.keys() and user['reg_no']:
                role_from_db = 'student'

        conn.close()

        session['user_id'] = user['id'] if user and isinstance(user, sqlite3.Row) and 'id' in user.keys() else 1
        session['username'] = db_username
        session['name'] = name or db_username
        session['role'] = role_from_db

        if role_from_db == 'student':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('submissions'))

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
    username = session.get('username')
    display_name = session.get('name')

    cursor.execute("SELECT * FROM faculty WHERE username = ?", (username,))
    faculty = cursor.fetchone()

    if not faculty:
        cursor.execute("SELECT * FROM faculty WHERE full_name = ?", (display_name,))
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
        full_name = request.form.get('full_name') or session.get('name') or session.get('username')
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

        username = session.get('username')
        cursor.execute("SELECT * FROM faculty WHERE username = ?", (username,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE faculty SET
                    username=?,
                    full_name=?,
                    employee_id=?,
                    designation=?,
                    department=?,
                    email=?,
                    phone=?,
                    office_room=?,
                    qualification=?,
                    specialization=?,
                    experience=?,
                    subjects_handling=?,
                    current_subjects=?,
                    research_areas=?,
                    bio=?,
                    philosophy=?
                WHERE username=?
            ''', (
                username,
                full_name,
                employee_id,
                designation,
                department,
                email,
                phone,
                office_room,
                qualification,
                specialization,
                experience,
                subjects_handling,
                current_subjects,
                research_areas,
                bio,
                philosophy,
                username,
            ))
        else:
            cursor.execute('''
                INSERT INTO faculty (
                    username, full_name, employee_id, designation, department, email,
                    phone, office_room, qualification, specialization, experience,
                    subjects_handling, current_subjects, research_areas, bio, philosophy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                full_name,
                employee_id,
                designation,
                department,
                email,
                phone,
                office_room,
                qualification,
                specialization,
                experience,
                subjects_handling,
                current_subjects,
                research_areas,
                bio,
                philosophy,
            ))

        session['name'] = full_name
        session['username'] = username
        conn.commit()
        conn.close()
        return redirect(url_for('faculty_profile'))

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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    student = None

    if session.get('user_id'):
        cursor.execute("SELECT * FROM students WHERE id = ?", (session.get('user_id'),))
        student = cursor.fetchone()

    if student is None and session.get('username'):
        cursor.execute("SELECT * FROM students WHERE username = ?", (session.get('username'),))
        student = cursor.fetchone()

    assignments = conn.execute('SELECT * FROM assignments').fetchall()
    student_dict = row_to_dict(student)
    submitted_count = conn.execute(
        'SELECT COUNT(*) AS count FROM submissions WHERE student_name = ?',
        (student_dict.get('full_name') or session.get('name') or session.get('username'),)
    ).fetchone()['count']
    conn.close()

    return render_template(
        'student_dashboard.html',
        student=student_dict,
        assignments=assignments,
        submitted_count=submitted_count,
        completed_count=0,
        pending_count=max(0, len(assignments) - submitted_count),
        progress_percentage=min(100, int((submitted_count / len(assignments)) * 100)) if assignments else 0,
    )

@app.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    file = request.files.get('file')
    if not file or not file.filename:
        return redirect(url_for('assignments_list'))

    conn = get_db_connection()
    cursor = conn.cursor()
    assignment = cursor.execute('SELECT * FROM assignments WHERE id = ?', (assignment_id,)).fetchone()
    student = cursor.execute('SELECT * FROM students WHERE id = ?', (session.get('user_id'),)).fetchone()
    conn.close()

    if not assignment or not student:
        return redirect(url_for('assignments_list'))

    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{session.get('username')}_{assignment_id}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    stored_path = f"static/uploads/{filename}"
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO submissions (assignment_title, student_name, reg_no, class_name, year, file_path, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            assignment['title'],
            student['full_name'],
            student['reg_no'],
            student['class_name'],
            student['year'],
            stored_path,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/assignments')
def assignments_list():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    assignments_list = conn.execute('SELECT * FROM assignments').fetchall()
    conn.close()
    return render_template('assignments.html', assignments=assignments_list)

@app.route('/profile')
def profile():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    user = None

    if session.get('user_id'):
        cursor.execute("SELECT * FROM students WHERE id = ?", (session.get('user_id'),))
        user = cursor.fetchone()

    if user is None and session.get('username'):
        cursor.execute("SELECT * FROM students WHERE username = ?", (session.get('username'),))
        user = cursor.fetchone()

    if user is None and session.get('name'):
        cursor.execute("SELECT * FROM students WHERE full_name = ? OR username = ?", (session.get('name'), session.get('name')))
        user = cursor.fetchone()

    conn.close()
    user_dict = row_to_dict(user)
    if user_dict and not user_dict.get('name') and user_dict.get('full_name'):
        user_dict['name'] = user_dict['full_name']

    return render_template('student_profile.html', user=user_dict)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') or request.form.get('role', 'student')
        reg_no = request.form.get('reg_no')
        class_name = request.form.get('class_name')
        year = request.form.get('year')

        conn = get_db_connection()
        cursor = conn.cursor()

        if role == 'faculty':
            cursor.execute(
                '''
                INSERT INTO faculty (username, full_name, email, department, designation, role)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (full_name, full_name, email, 'General', 'Professor', role)
            )
        else:
            cursor.execute(
                '''
                INSERT INTO students (username, full_name, reg_no, class_name, year, password, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (full_name, full_name, reg_no, class_name, year, password, role)
            )

        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)