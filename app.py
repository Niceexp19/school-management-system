from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'school2026secret'

DB_PATH = 'school.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        class TEXT NOT NULL,
        gender TEXT NOT NULL,
        parent_name TEXT,
        parent_phone TEXT,
        address TEXT,
        date_enrolled TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        term TEXT NOT NULL,
        session TEXT NOT NULL,
        teacher TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        class TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        term TEXT NOT NULL,
        session TEXT NOT NULL,
        status TEXT NOT NULL,
        date_paid TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        date TEXT NOT NULL,
        author TEXT NOT NULL
    )''')

    # Create default admin account
    try:
        c.execute('INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)',
                 ['admin', 'admin123', 'admin', 'School Administrator', 'admin@school.com'])
        # Create demo teacher
        c.execute('INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)',
                 ['teacher1', 'teacher123', 'teacher', 'Mr. James Okafor', 'james@school.com'])
        conn.commit()
    except:
        pass

    conn.close()
init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?',
                         [username, password]).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            return redirect(url_for('dashboard'))
        else:
            message = 'Invalid us
ername or password!'
    return render_template('login.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_teachers = db.execute('SELECT COUNT(*) FROM users WHERE role = ?', ['teacher']).fetchone()[0]
    total_announcements = db.execute('SELECT COUNT(*) FROM announcements').fetchone()[0]
    announcements = db.execute('SELECT * FROM announcements ORDER BY id DESC LIMIT 5').fetchall()
    recent_students = db.execute('SELECT * FROM students ORDER BY id DESC LIMIT 5').fetchall()
    db.close()
    return render_template('dashboard.html',
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_announcements=total_announcements,
                         announcements=announcements,
                         recent_students=recent_students)

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    message = ''
    if request.method == 'POST' and session.get('role') == 'admin':
        full_name = request.form['full_name']
        class_ = request.form['class']
        gender = request.form['gender']
        parent_name = request.form['parent_name']
        parent_phone = request.form['parent_phone']
        address = request.form['address']
        date_enrolled = request.form['date_enrolled']
        db = get_db()
        db.execute('INSERT INTO students (full_name, class, gender, parent_name, parent_phone, address, date_enrolled) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  [full_name, class_, gender, parent_name, parent_phone, address, date_enrolled])
        db.commit()
        db.close()
        message = 'Student registered successfully! ✅'

    db = get_db()
    search = request.args.get('search', '')
    class_filter = request.args.get('class', '')
    if search:
        students = db.execute('SELECT * FROM students WHERE full_name LIKE ? ORDER BY full_name',
                            ['%'+search+'%']).fetchall()
    elif class_filter:
        students = db.execute('SELECT * FROM students WHERE class = ? ORDER BY full_name',
                            [class_filter]).fetchall()
    else:
        students = db.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    total = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    db.close()
    return render_template('students.html',
                         students=students,
                         message=message,
                         search=search,
                         class_filter=class_filter,
                         total=total)

@app.route('/delete_student/<int:id>')
@login_required
@admin_required
def delete_student(id):
    db = get_db()
    db.execute('DELETE FROM students WHERE id = ?', [id])
    db.execute('DELETE FROM grades WHERE student_id = ?', [id])
    db.execute('DELETE FROM attendance WHERE student_id = ?', [id])
    db.execute('DELETE FROM fees WHERE student_id = ?', [id])
    db.commit()
    db.close()
    return redirect(url_for('students'))

@app.route('/grades', methods=['GET', 'POST'])
@login_required
def grades():
    message = ''
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        score = float(request.form['score'])
        term = request.form['term']
        session_ = request.form['session']
        db = get_db()
        db.execute('INSERT INTO grades (student_id, subject, score, term, session, teacher) VALUES (?, ?, ?, ?, ?, ?)',
                  [student_id, subject, score, term, session_, session['full_name']])
        db.commit()
        db.close()
        message = 'Grade recorded successfully! ✅'

    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    grades = db.execute('''SELECT g.*, s.full_name, s.class 
                          FROM grades g 
                          JOIN students s ON g.student_id = s.id 
                          ORDER BY g.id DESC''').fetchall()
    db.close()
    return render_template('grades.html',
                         students=students,
                         grades=grades,
                         message=message)

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    message = ''
    if request.method == 'POST':
        date = request.form['date']
        class_ = request.form['class']
        db = get_db()
        students = db.execute('SELECT * FROM students WHERE class = ?', [class_]).fetchall()
        for student in students:
            status = request.form.get(f'status_{student["id"]}', 'absent')
            db.execute('INSERT INTO attendance (student_id, date, status, class) VALUES (?, ?, ?, ?)',
                      [student['id'], date, status, class_])
        db.commit()
        db.close()
        message = 'Attendance recorded successfully! ✅'

    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY class, full_name').fetchall()
    attendance = db.execute('''SELECT a.*, s.full_name, s.class 
                              FROM attendance a 
                              JOIN students s ON a.student_id = s.id 
                              ORDER BY a.date DESC LIMIT 50''').fetchall()
    db.close()
    return render_template('attendance.html',
                         students=students,
                         attendance=attendance,
                         message=message)

@app.route('/fees', methods=['GET', 'POST'])
@login_required
def fees():
    message = ''
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = float(request.form['amount'])
        term = request.form['term']
        session_ = request.form['session']
        status = request.form['status']
        date_paid = request.form.get('date_paid', '')
        db = get_db()
        db.execute('INSERT INTO fees (student_id, amount, term, session, status, date_paid) VALUES (?, ?, ?, ?, ?, ?)',
                  [student_id, amount, term, session_, status, date_paid])
        db.commit()
        db.close()
        message = 'Fee record saved! ✅'

    db = get_db()
    students = db.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    fees = db.execute('''SELECT f.*, s.full_name, s.class 
                        FROM fees f 
                        JOIN students s ON f.student_id = s.id 
                        ORDER BY f.id DESC''').fetchall()
    total_paid = db.execute('SELECT SUM(amount) FROM fees WHERE status = ?', ['paid']).fetchone()[0] or 0
    total_pending = db.execute('SELECT SUM(amount) FROM fees WHERE status = ?', ['pending']).fetchone()[0] or 0
    db.close()
    return render_template('fees.html',
                         students=students,
                         fees=fees,
                         message=message,
                         total_paid=total_paid,
@app.route('/announcements', methods=['GET', 'POST'])
@login_required
def announcements():
    message = ''
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        from datetime import date
        db = get_db()
        db.execute('INSERT INTO announcements (title, content, date, author) VALUES (?, ?, ?, ?)',
                  [title, content, str(date.today()), session['full_name']])
        db.commit()
        db.close()
        message = 'Announcement posted! ✅'

    db = get_db()
    announcements = db.execute('SELECT * FROM announcements ORDER BY id DESC').fetchall()
    db.close()
    return render_template('announcements.html',
                         announcements=announcements,
                         message=message)

@app.route('/delete_announcement/<int:id>')
@login_required
@admin_required
def delete_announcement(id):
    db = get_db()
    db.execute('DELETE FROM announcements WHERE id = ?', [id])
    db.commit()
    db.close()
    return redirect(url_for('announcements'))

@app.route('/report/<int:student_id>')
@login_required
def report(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ?', [student_id]).fetchone()
    grades = db.execute('SELECT * FROM grades WHERE student_id = ? ORDER BY subject',
                       [student_id]).fetchall()
    attendance = db.execute('SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = ?',
                           [student_id, 'present']).fetchone()[0]
    total_days = db.execute('SELECT COUNT(*) FROM attendance WHERE student_id = ?',
                           [student_id]).fetchone()[0]
    fees = db.execute('SELECT * FROM fees WHERE student_id = ?', [student_id]).fetchall()
    db.close()
    return render_template('report.html',
                         student=student,
                         grades=grades,
                         attendance=attendance,
                         total_days=total_days,
                         fees=fees)

if __name__ == '__main__':
    app.run(debug=True)                         total_pending=total_pending)


