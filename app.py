from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Attendance, Marks
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_system.db'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Decorator for Roles
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("Access Denied!")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']: # Use hashing in production
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/')
@login_required
def dashboard():
    if current_user.role == 'student':
        # Students see only their approved marks
        my_marks = Marks.query.filter_by(student_id=current_user.id, status='Approved').all()
        return render_template('student_dash.html', marks=my_marks)
    
    elif current_user.role == 'teacher':
        # Teachers see all students to mark attendance/marks
        students = User.query.filter_by(role='student').all()
        return render_template('teacher_dash.html', students=students)
    
    elif current_user.role == 'admin':
        # Admins see marks awaiting approval
        pending_marks = Marks.query.filter_by(status='Pending').all()
        return render_template('admin_dash.html', pending=pending_marks)

@app.route('/add_marks/<int:sid>', methods=['POST'])
@role_required(['teacher'])
def add_marks(sid):
    new_mark = Marks(student_id=sid, subject=request.form['subject'], 
                     score=request.form['score'], status='Pending')
    db.session.add(new_mark)
    db.session.commit()
    flash("Marks submitted for admin approval.")
    return redirect(url_for('dashboard'))

@app.route('/approve/<int:mid>')
@role_required(['admin'])
def approve_mark(mid):
    mark = Marks.query.get(mid)
    mark.status = 'Approved'
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create a test admin if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password='123', role='admin', name='Head Admin')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)