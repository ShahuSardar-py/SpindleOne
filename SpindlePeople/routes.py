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
@bp.route('/')
def index():
    return redirect(url_for('spindlepeople.employee'))

@bp.route('/dashboard')
def dashboard():
    today = datetime.utcnow().date()

    # --- Employees ---
    employees = Employee.query.all()
    total_employees = len(employees)

    total_payroll = sum(emp.salary for emp in employees)
    avg_salary = (total_payroll / total_employees) if total_employees > 0 else 0

    # Role distribution
    from collections import Counter
    roles = Counter(emp.position for emp in employees)

    role_labels = list(roles.keys())
    role_counts = list(roles.values())

    # --- Today's Attendance ---
    today_records = Attendance.query.filter_by(date=today).all()

    present_today = sum(1 for r in today_records if r.status == 'Present')
    absent_today = total_employees - present_today

    attendance_rate = (present_today / total_employees * 100) if total_employees > 0 else 0

    # Late logins (after 10 AM)
    late_logins = sum(
        1 for r in today_records 
        if r.login_time and r.login_time.hour >= 10
    )

    # Not logged out
    not_logged_out = sum(
        1 for r in today_records if r.logout_time is None
    )

    # --- Working Hours ---
    working_hours = []

    for r in today_records:
        if r.login_time and r.logout_time:
            duration = (r.logout_time - r.login_time).total_seconds() / 3600
            working_hours.append(duration)

    avg_working_hours = (
        sum(working_hours) / len(working_hours)
        if working_hours else 0
    )

    top_performer = max(working_hours) if working_hours else 0
    least_active = min(working_hours) if working_hours else 0

    # --- Last 7 Days Trend ---
    from datetime import timedelta

    days = []
    present_counts = []
    absent_counts = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_records = Attendance.query.filter_by(date=day).all()

        present = sum(1 for r in day_records if r.status == 'Present')
        absent = total_employees - present

        days.append(day.strftime('%d %b'))
        present_counts.append(present)
        absent_counts.append(absent)

    # --- Render ---
    return render_template(
        'dashboard.html',

        # Workforce
        total_employees=total_employees,
        total_payroll=total_payroll,
        avg_salary=avg_salary,

        # Attendance
        present_today=present_today,
        absent_today=absent_today,
        attendance_rate=attendance_rate,
        late_logins=late_logins,
        not_logged_out=not_logged_out,

        # Productivity
        avg_working_hours=avg_working_hours,
        top_performer=top_performer,
        least_active=least_active,

        # Charts
        days=days,
        present_counts=present_counts,
        absent_counts=absent_counts,
        role_labels=role_labels,
        role_counts=role_counts
    )

@bp.route('/employees',methods=['GET'])
def employee():
    employees= Employee.query.all()
    return render_template('employees.html', employees=employees)

@bp.route('/employees/add', methods=['GET','POST'])
def add_employee():
    if request.method =='POST':
        emp= Employee(
            name=request.form['name'],
            position=request.form['position'],
            salary=float(request.form['salary'])
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