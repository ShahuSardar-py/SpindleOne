from datetime import datetime
from app.extensions import db   # adjust if your db lives elsewhere


class Machine(db.Model):
    __tablename__ = 'mech_machines'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    machine_code  = db.Column(db.String(60),  unique=True, nullable=False)   # e.g. MCH-001
    category      = db.Column(db.String(80))
    manufacturer  = db.Column(db.String(120))
    model_number  = db.Column(db.String(80))
    serial_number = db.Column(db.String(80))
    purchase_date = db.Column(db.Date)
    location      = db.Column(db.String(120))
    status        = db.Column(db.String(30), default='Operational')   # Operational | Under Maintenance | Decommissioned
    notes         = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship(
        'MaintenanceRecord',
        backref='machine',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Machine {self.machine_code} – {self.name}>'

    @property
    def last_maintenance(self):
        rec = self.records.order_by(MaintenanceRecord.performed_on.desc()).first()
        return rec.performed_on if rec else None

    @property
    def total_cost(self):
        return sum(r.cost or 0 for r in self.records)


class MaintenanceRecord(db.Model):
    __tablename__ = 'mech_maintenance_records'

    id               = db.Column(db.Integer, primary_key=True)
    machine_id       = db.Column(db.Integer, db.ForeignKey('mech_machines.id'), nullable=False)
    maintenance_type = db.Column(db.String(60), nullable=False)   # Preventive | Corrective | Inspection
    performed_by     = db.Column(db.String(120))
    performed_on     = db.Column(db.Date, nullable=False)
    next_due         = db.Column(db.Date)
    cost             = db.Column(db.Float)
    downtime_hours   = db.Column(db.Float)
    description      = db.Column(db.Text, nullable=False)
    parts_replaced   = db.Column(db.Text)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MaintenanceRecord {self.id} – machine {self.machine_id}>'