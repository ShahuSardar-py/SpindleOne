from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from SpindlePeople.models import Employee, Attendance
from datetime import datetime
from flask import jsonify

bp = Blueprint(
    'spindlepeople',
    __name__,
    url_prefix='/hr',
    template_folder='templates',
    static_folder='static'
)


@bp.route('/employees',methods=['GET'])
def employee():
    employees= Employee.query.all()
    return render_template('employees.html', employees=employees)

@bp.route('/employees/add', methods=['GET','POST'])
def add_employee():
    if request.method =='POST':
        emp= Employee(
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
    return render_template('employee_detail.html', employee=employee)


@bp.route('/employees/<int:emp_id>/data')
def employee_detail_data(emp_id):
    employee = Employee.query.get_or_404(emp_id)
    return jsonify({
        "id": employee.id,
        "name": employee.name,
        "position": employee.position,
        "salary": employee.salary
    })




@bp.route('/logattendance')
def logattendance():
    employees = Employee.query.all()
    today = datetime.utcnow().date()
    today_attendance = Attendance.query.filter_by(date=today).all()
    attendance_records = {record.employee_id: record for record in today_attendance}
    return render_template('Logattendance.html', employees=employees, attendance_records=attendance_records)

@bp.route('/logattendance/login/<int:emp_id>', methods=['POST'])
def login(emp_id):
    record = Attendance(
        employee_id=emp_id,
        status='Present',
        login_time=datetime.now()
    )
    db.session.add(record)
    db.session.commit()
    return redirect(url_for('spindlepeople.logattendance'))

@bp.route('/logattendance/logout/<int:emp_id>', methods=['POST'])
def logout(emp_id):
    record = Attendance.query.filter_by(
        employee_id=emp_id,
        date=datetime.utcnow().date()
    ).first()

    if record:
        record.logout_time = datetime.now()
        db.session.commit()

    return redirect(url_for('spindlepeople.logattendance'))

@bp.route('/attendance')
def attendance():
    records= Attendance.query.join(Employee).order_by(Attendance.date.desc(), Attendance.login_time.desc()).all()
    return render_template('attendance.html', records=records)