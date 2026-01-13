from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app.extensions import db
from SpindlePeople.models import Employee, Attendance
from datetime import datetime

bp = Blueprint(
    'spindlepeople',
    __name__,
    url_prefix='/hr',
    template_folder='templates',
    static_folder='static'
)


@bp.route('/')
@bp.route('/employees', methods=['GET'])
def employee():
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)

@bp.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        emp = Employee(
            id=request.form['id'],
            name=request.form['name'],
            position=request.form['position'],
            salary=request.form['salary']
        )
        db.session.add(emp)
        db.session.commit()
        return redirect(url_for('spindlepeople.employee'))
    return render_template('add_employee.html')

@bp.route('/employees/<int:emp_id>')
def employee_detail(emp_id):
    employee = Employee.query.get_or_404(emp_id)
    return jsonify({
        'id': employee.id,
        'name': employee.name,
        'position': employee.position,
        'salary': employee.salary
    })

@bp.route('/attendance')
def attendance():
    employees = Employee.query.all()
    # Get today's attendance records
    today = datetime.utcnow().date()
    attendance_records = {}
    for emp in employees:
        record = Attendance.query.filter_by(
            employee_id=emp.id,
            date=today
        ).first()
        attendance_records[emp.id] = record
    
    return render_template('attendance.html', employees=employees, attendance_records=attendance_records)

@bp.route('/attendance/login/<int:emp_id>', methods=['POST'])
def login(emp_id):
    # Check if already logged in today
    today = datetime.utcnow().date()
    existing = Attendance.query.filter_by(
        employee_id=emp_id,
        date=today
    ).first()
    
    if not existing:
        record = Attendance(
            employee_id=emp_id,
            status='Present',
            login_time=datetime.now(),
            date=today
        )
        db.session.add(record)
        db.session.commit()
    
    return redirect(url_for('spindlepeople.attendance'))

@bp.route('/attendance/logout/<int:emp_id>', methods=['POST'])
def logout(emp_id):
    record = Attendance.query.filter_by(
        employee_id=emp_id,
        date=datetime.utcnow().date()
    ).first()

    if record:
        record.logout_time = datetime.now()
        db.session.commit()

    return redirect(url_for('spindlepeople.attendance'))