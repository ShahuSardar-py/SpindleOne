from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash
from app.extensions import db
from .models import Machine, MaintenanceRecord
from . import bp


# ---------------------------------------------------------------------------
# Dashboard – machine list
# ---------------------------------------------------------------------------

@bp.route('/')
def index():
    machines = Machine.query.order_by(Machine.name).all()
    total          = len(machines)
    operational    = sum(1 for m in machines if m.status == 'Operational')
    under_maint    = sum(1 for m in machines if m.status == 'Under Maintenance')
    decommissioned = sum(1 for m in machines if m.status == 'Decommissioned')
    return render_template(
        'spindlemech/index.html',
        machines=machines,
        total=total,
        operational=operational,
        under_maint=under_maint,
        decommissioned=decommissioned,
    )


# ---------------------------------------------------------------------------
# Add machine
# ---------------------------------------------------------------------------

@bp.route('/machines/add', methods=['GET', 'POST'])
def add_machine():
    if request.method == 'POST':
        purchase_date = None
        raw = request.form.get('purchase_date', '').strip()
        if raw:
            try:
                purchase_date = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                pass

        machine = Machine(
            name          = request.form['name'].strip(),
            machine_code  = request.form['machine_code'].strip().upper(),
            category      = request.form.get('category', '').strip(),
            manufacturer  = request.form.get('manufacturer', '').strip(),
            model_number  = request.form.get('model_number', '').strip(),
            serial_number = request.form.get('serial_number', '').strip(),
            purchase_date = purchase_date,
            location      = request.form.get('location', '').strip(),
            status        = request.form.get('status', 'Operational'),
            notes         = request.form.get('notes', '').strip(),
        )
        db.session.add(machine)
        try:
            db.session.commit()
            flash('Machine added successfully.', 'success')
            return redirect(url_for('spindlemech.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding machine: {e}', 'error')

    return render_template('spindlemech/add_machine.html')


# ---------------------------------------------------------------------------
# Machine detail + maintenance history
# ---------------------------------------------------------------------------

@bp.route('/machines/<int:machine_id>')
def machine_detail(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    records = machine.records.order_by(MaintenanceRecord.performed_on.desc()).all()
    return render_template('spindlemech/machine_detail.html', machine=machine, records=records)


# ---------------------------------------------------------------------------
# Edit machine
# ---------------------------------------------------------------------------

@bp.route('/machines/<int:machine_id>/edit', methods=['GET', 'POST'])
def edit_machine(machine_id):
    machine = Machine.query.get_or_404(machine_id)
    if request.method == 'POST':
        machine.name          = request.form['name'].strip()
        machine.machine_code  = request.form['machine_code'].strip().upper()
        machine.category      = request.form.get('category', '').strip()
        machine.manufacturer  = request.form.get('manufacturer', '').strip()
        machine.model_number  = request.form.get('model_number', '').strip()
        machine.serial_number = request.form.get('serial_number', '').strip()
        machine.location      = request.form.get('location', '').strip()
        machine.status        = request.form.get('status', machine.status)
        machine.notes         = request.form.get('notes', '').strip()
        raw = request.form.get('purchase_date', '').strip()
        if raw:
            try:
                machine.purchase_date = datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                pass
        try:
            db.session.commit()
            flash('Machine updated.', 'success')
            return redirect(url_for('spindlemech.machine_detail', machine_id=machine.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'error')

    return render_template('spindlemech/edit_machine.html', machine=machine)


# ---------------------------------------------------------------------------
# Log maintenance record  (can pick machine from dropdown)
# ---------------------------------------------------------------------------

@bp.route('/maintenance/log', methods=['GET', 'POST'])
def log_maintenance():
    """Standalone maintenance log form – machine selected via dropdown."""
    machines = Machine.query.order_by(Machine.name).all()

    if request.method == 'POST':
        try:
            performed_on = datetime.strptime(request.form['performed_on'], '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date.', 'error')
            return render_template('spindlemech/log_maintenance.html',
                                   machines=machines, today=date.today().isoformat())

        next_due = None
        if request.form.get('next_due', '').strip():
            try:
                next_due = datetime.strptime(request.form['next_due'], '%Y-%m-%d').date()
            except ValueError:
                pass

        cost = None
        if request.form.get('cost', '').strip():
            try:
                cost = float(request.form['cost'])
            except ValueError:
                pass

        downtime = None
        if request.form.get('downtime_hours', '').strip():
            try:
                downtime = float(request.form['downtime_hours'])
            except ValueError:
                pass

        record = MaintenanceRecord(
            machine_id       = int(request.form['machine_id']),
            maintenance_type = request.form['maintenance_type'],
            performed_by     = request.form.get('performed_by', '').strip(),
            performed_on     = performed_on,
            next_due         = next_due,
            cost             = cost,
            downtime_hours   = downtime,
            description      = request.form['description'].strip(),
            parts_replaced   = request.form.get('parts_replaced', '').strip(),
        )
        db.session.add(record)
        try:
            db.session.commit()
            flash('Maintenance record logged.', 'success')
            return redirect(url_for('spindlemech.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving record: {e}', 'error')

    # pre-select machine if coming from machine detail page
    preselect = request.args.get('machine_id', type=int)
    return render_template('spindlemech/log_maintenance.html',
                           machines=machines,
                           preselect=preselect,
                           today=date.today().isoformat())


# ---------------------------------------------------------------------------
# Delete maintenance record
# ---------------------------------------------------------------------------

@bp.route('/maintenance/<int:record_id>/delete', methods=['POST'])
def delete_maintenance(record_id):
    record = MaintenanceRecord.query.get_or_404(record_id)
    machine_id = record.machine.id
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted.', 'success')
    return redirect(url_for('spindlemech.machine_detail', machine_id=machine_id))