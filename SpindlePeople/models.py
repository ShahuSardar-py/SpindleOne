from datetime import datetime
from app.extensions import db

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Float, nullable=False)

    emp_attendance = db.relationship('Attendance', backref='employee', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    status = db.Column(db.String(10))  # Present / Absent
    login_time = db.Column(db.DateTime)
    logout_time = db.Column(db.DateTime)
    date = db.Column(db.Date, default=datetime.utcnow().date)

