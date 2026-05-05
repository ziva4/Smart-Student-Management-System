from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


# ---------------- USER MODEL ---------------- #

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    role = db.Column(db.String(20), nullable=False)  
    # 'admin', 'teacher', 'student'

    name = db.Column(db.String(100))

    # 🔥 NEW: Teacher approval system
    is_approved = db.Column(db.Boolean, default=False)

    # Relationships
    marks = db.relationship('Marks', backref='student', lazy=True)
    attendance = db.relationship('Attendance', backref='student', lazy=True)


# ---------------- ATTENDANCE MODEL ---------------- #

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    date = db.Column(db.String(20))  
    # (You can later upgrade to Date type)

    status = db.Column(db.String(10))  
    # 'Present' or 'Absent'

    # 🔥 NEW: timestamp (useful for analytics)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- MARKS MODEL ---------------- #

class Marks(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    subject = db.Column(db.String(50))
    score = db.Column(db.Integer)

    status = db.Column(db.String(20), default='Pending')  
    # 'Pending' or 'Approved'

    # 🔥 NEW: timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)