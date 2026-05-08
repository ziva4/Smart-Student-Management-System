from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from models import db, User, Attendance, Marks
from functools import wraps
from datetime import datetime


# ---------------- APP CONFIG ---------------- #

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_smart_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_system.db'

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------- LOGIN MANAGER ---------------- #

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- ROLE PROTECTION ---------------- #

def role_required(roles):

    def decorator(f):

        @wraps(f)
        def wrapper(*args, **kwargs):

            if (
                not current_user.is_authenticated
                or current_user.role not in roles
            ):

                flash("Unauthorized Access!")
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)

        return wrapper

    return decorator


# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        user = User.query.filter_by(
            username=request.form['username']
        ).first()

        if user and user.password == request.form['password']:

            # Teacher approval check
            if (
                user.role == "teacher"
                and not user.is_approved
            ):

                flash("Wait for admin approval")
                return redirect(url_for('login'))

            login_user(user)

            return redirect(url_for('dashboard'))

        flash("Invalid username or password")

    return render_template('login.html')


# ---------------- REGISTER ---------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form.get('username')

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash("Username already exists")

            return redirect(url_for('register'))

        role = request.form.get('role')

        new_user = User(
            username=username,
            password=request.form.get('password'),
            name=request.form.get('name'),
            role=role,
            is_approved=False if role == "teacher" else True
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!")

        return redirect(url_for('login'))

    return render_template('register.html')


# ---------------- DASHBOARD ---------------- #

@app.route('/')
@login_required
def dashboard():

    # ---------------- STUDENT ---------------- #

    if current_user.role == 'student':

        marks = Marks.query.filter_by(
            student_id=current_user.id,
            status='Approved'
        ).all()

        attendance = Attendance.query.filter_by(
            student_id=current_user.id
        ).all()

        total = len(attendance)

        present = len([
            a for a in attendance
            if a.status == "Present"
        ])

        percent = (
            (present / total) * 100
            if total > 0 else 0
        )

        alert = None

        if percent < 75:
            alert = "Low Attendance Warning!"

        return render_template(
            'student_dash.html',
            marks=marks,
            attendance=attendance,
            percent=round(percent, 2),
            alert=alert
        )

    # ---------------- TEACHER ---------------- #

    elif current_user.role == 'teacher':

        students = User.query.filter_by(
            role='student'
        ).all()

        return render_template(
            'teacher_dash.html',
            students=students
        )

    # ---------------- ADMIN ---------------- #

    else:

        pending_marks = Marks.query.filter_by(
            status='Pending'
        ).all()

        pending_teachers = User.query.filter_by(
            role='teacher',
            is_approved=False
        ).all()

        students = User.query.filter_by(
            role='student'
        ).all()

        teachers = User.query.filter_by(
            role='teacher'
        ).all()

        return render_template(
            'admin_dash.html',
            pending_marks=pending_marks,
            pending_teachers=pending_teachers,
            students=students,
            teachers=teachers
        )


# ---------------- STUDENT DETAIL ---------------- #

@app.route('/student/<int:sid>')
@role_required(['teacher'])
def student_detail(sid):

    student = User.query.get(sid)

    marks = Marks.query.filter_by(
        student_id=sid
    ).all()

    attendance = Attendance.query.filter_by(
        student_id=sid
    ).all()

    return render_template(
        'student_detail.html',
        student=student,
        marks=marks,
        attendance=attendance
    )


# ---------------- MARKS ---------------- #

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

    flash("Marks added")

    return redirect(url_for(
        'student_detail',
        sid=sid
    ))


@app.route('/edit_mark/<int:mid>', methods=['POST'])
@role_required(['teacher'])
def edit_mark(mid):

    mark = Marks.query.get(mid)

    mark.subject = request.form['subject']
    mark.score = request.form['score']
    mark.status = "Pending"

    db.session.commit()

    flash("Marks updated")

    return redirect(url_for(
        'student_detail',
        sid=mark.student_id
    ))


@app.route('/delete_mark/<int:mid>')
@role_required(['teacher'])
def delete_mark(mid):

    mark = Marks.query.get(mid)

    sid = mark.student_id

    db.session.delete(mark)
    db.session.commit()

    flash("Marks deleted")

    return redirect(url_for(
        'student_detail',
        sid=sid
    ))


# ---------------- ATTENDANCE ---------------- #

@app.route('/mark_attendance/<int:sid>', methods=['POST'])
@role_required(['teacher'])
def mark_attendance(sid):

    existing = Attendance.query.filter_by(
        student_id=sid,
        date=request.form['date']
    ).first()

    if existing:

        flash("Attendance already exists")

        return redirect(url_for(
            'student_detail',
            sid=sid
        ))

    record = Attendance(
        student_id=sid,
        date=request.form['date'],
        status=request.form['status']
    )

    db.session.add(record)
    db.session.commit()

    flash("Attendance added")

    return redirect(url_for(
        'student_detail',
        sid=sid
    ))


@app.route('/toggle_attendance/<int:aid>', methods=['POST'])
@role_required(['teacher'])
def toggle_attendance(aid):

    attendance = Attendance.query.get(aid)

    if attendance.status == "Present":
        attendance.status = "Absent"
    else:
        attendance.status = "Present"

    db.session.commit()

    flash("Attendance updated")

    return redirect(url_for(
        'student_detail',
        sid=attendance.student_id
    ))


@app.route('/delete_attendance/<int:aid>')
@role_required(['teacher'])
def delete_attendance(aid):

    attendance = Attendance.query.get(aid)

    sid = attendance.student_id

    db.session.delete(attendance)
    db.session.commit()

    flash("Attendance deleted")

    return redirect(url_for(
        'student_detail',
        sid=sid
    ))


# ---------------- QUICK ATTENDANCE ---------------- #

@app.route('/quick_attendance/<int:sid>/<status>', methods=['POST'])
@role_required(['teacher'])
def quick_attendance(sid, status):

    today = datetime.now().strftime("%Y-%m-%d")

    existing = Attendance.query.filter_by(
        student_id=sid,
        date=today
    ).first()

    if existing:

        existing.status = status

        flash("Attendance updated")

    else:

        attendance = Attendance(
            student_id=sid,
            date=today,
            status=status
        )

        db.session.add(attendance)

        flash("Attendance marked")

    db.session.commit()

    return redirect(url_for('dashboard'))


# ---------------- ADMIN ---------------- #

@app.route('/approve_mark/<int:mid>')
@role_required(['admin'])
def approve_mark(mid):

    mark = Marks.query.get(mid)

    mark.status = "Approved"

    db.session.commit()

    flash("Marks approved")

    return redirect(url_for('dashboard'))


@app.route('/approve_teacher/<int:uid>')
@role_required(['admin'])
def approve_teacher(uid):

    user = User.query.get(uid)

    user.is_approved = True

    db.session.commit()

    flash("Teacher approved")

    return redirect(url_for('dashboard'))


# DELETE STUDENT
@app.route('/delete_student/<int:uid>')
@role_required(['admin'])
def delete_student(uid):

    user = User.query.get(uid)

    Marks.query.filter_by(
        student_id=uid
    ).delete()

    Attendance.query.filter_by(
        student_id=uid
    ).delete()

    db.session.delete(user)

    db.session.commit()

    flash("Student deleted")

    return redirect(url_for('dashboard'))


# DELETE TEACHER
@app.route('/delete_teacher/<int:uid>')
@role_required(['admin'])
def delete_teacher(uid):

    user = User.query.get(uid)

    db.session.delete(user)

    db.session.commit()

    flash("Teacher deleted")

    return redirect(url_for('dashboard'))


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash("Logged out successfully")

    return redirect(url_for('login'))


# ---------------- RUN APP ---------------- #

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

        if not User.query.filter_by(
            role='admin'
        ).first():

            admin = User(
                username='admin',
                password='123',
                role='admin',
                name='System Admin',
                is_approved=True
            )

            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)