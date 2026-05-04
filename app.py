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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("Unauthorized Access!")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid Username or Password")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username,
            password=request.form.get('password'),
            name=request.form.get('name'),
            role=request.form.get('role')
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
@login_required
def dashboard():
    if current_user.role == 'student':
        marks = Marks.query.filter_by(student_id=current_user.id, status='Approved').all()
        return render_template('student_dash.html', marks=marks)
    elif current_user.role == 'teacher':
        students = User.query.filter_by(role='student').all()
        return render_template('teacher_dash.html', students=students)
    else:
        pending = Marks.query.filter_by(status='Pending').all()
        return render_template('admin_dash.html', pending=pending)

@app.route('/add_marks/<int:sid>', methods=['POST'])
@role_required(['teacher'])
def add_marks(sid):
    new_mark = Marks(student_id=sid, subject=request.form['subject'], score=request.form['score'])
    db.session.add(new_mark)
    db.session.commit()
    flash("Marks submitted for approval.")
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
        if not User.query.filter_by(role='admin').first():
            admin = User(username='admin', password='123', role='admin', name='System Admin')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)