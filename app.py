from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Attendance, Marks
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_smart_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_system.db'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------- LOGIN ---------------- #

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- ROLE CHECK ---------------- #

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("Unauthorized!")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- AUTH ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and user.password == request.form['password']:

            # 🔥 TEACHER APPROVAL CHECK
            if user.role == "teacher" and not user.is_approved:
                flash("Wait for admin approval")
                return redirect(url_for('login'))

            login_user(user)
            return redirect(url_for('dashboard'))

        flash("Invalid credentials")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        role = request.form.get('role')

        new_user = User(
            username=request.form.get('username'),
            password=request.form.get('password'),
            name=request.form.get('name'),
            role=role,
            is_approved=False if role == "teacher" else True
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registered! Wait for approval if teacher.")
        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------- DASHBOARD ---------------- #

@app.route('/')
@login_required
def dashboard():

    if current_user.role == 'student':
        marks = Marks.query.filter_by(
            student_id=current_user.id,
            status='Approved'
        ).all()

        attendance = Attendance.query.filter_by(student_id=current_user.id).all()

        # 🔥 SMART ALERT
        total = len(attendance)
        present = len([a for a in attendance if a.status == "Present"])
        percent = (present / total * 100) if total else 0

        alert = None
        if percent < 75:
            alert = "Low Attendance Warning!"

        return render_template('student_dash.html', marks=marks, attendance=attendance, percent=percent, alert=alert)

    elif current_user.role == 'teacher':
        students = User.query.filter_by(role='student').all()
        return render_template('teacher_dash.html', students=students)

    else:
        pending_marks = Marks.query.filter_by(status='Pending').all()
        pending_teachers = User.query.filter_by(role='teacher', is_approved=False).all()

        return render_template('admin_dash.html', pending_marks=pending_marks, pending_teachers=pending_teachers)


# ---------------- TEACHER ---------------- #

@app.route('/student/<int:sid>')
@role_required(['teacher'])
def student_detail(sid):
    student = User.query.get(sid)
    marks = Marks.query.filter_by(student_id=sid).all()
    attendance = Attendance.query.filter_by(student_id=sid).all()
    return render_template('student_detail.html', student=student, marks=marks, attendance=attendance)


@app.route('/add_marks/<int:sid>', methods=['POST'])
@role_required(['teacher'])
def add_marks(sid):
    mark = Marks(
        student_id=sid,
        subject=request.form['subject'],
        score=request.form['score'],
        status="Pending"
    )
    db.session.add(mark)
    db.session.commit()
    return redirect(url_for('student_detail', sid=sid))


@app.route('/edit_mark/<int:mid>', methods=['POST'])
@role_required(['teacher'])
def edit_mark(mid):
    mark = Marks.query.get(mid)
    mark.subject = request.form['subject']
    mark.score = request.form['score']
    mark.status = "Pending"
    db.session.commit()
    return redirect(url_for('student_detail', sid=mark.student_id))


@app.route('/delete_mark/<int:mid>')
@role_required(['teacher'])
def delete_mark(mid):
    mark = Marks.query.get(mid)
    sid = mark.student_id
    db.session.delete(mark)
    db.session.commit()
    return redirect(url_for('student_detail', sid=sid))


# 📅 Attendance
@app.route('/mark_attendance/<int:sid>', methods=['POST'])
@role_required(['teacher'])
def mark_attendance(sid):
    record = Attendance(
        student_id=sid,
        date=request.form['date'],
        status=request.form['status']
    )
    db.session.add(record)
    db.session.commit()
    return redirect(url_for('student_detail', sid=sid))


# ---------------- ADMIN ---------------- #

@app.route('/approve_mark/<int:mid>')
@role_required(['admin'])
def approve_mark(mid):
    mark = Marks.query.get(mid)
    mark.status = "Approved"
    db.session.commit()
    return redirect(url_for('dashboard'))


# 🔥 APPROVE TEACHER
@app.route('/approve_teacher/<int:uid>')
@role_required(['admin'])
def approve_teacher(uid):
    user = User.query.get(uid)
    user.is_approved = True
    db.session.commit()
    return redirect(url_for('dashboard'))


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------------- RUN ---------------- #

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', password='123', role='admin', name='Admin', is_approved=True)
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)