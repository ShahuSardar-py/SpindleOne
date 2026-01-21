from datetime import datetime
from app.extensions import db 

class AccountCashflow(db.Model):
    __tablename__ ='AccountCashflow'

    id = db.Column(db.Integer, primary_key=True)
    txn_date = db.Column(db.Date, default=datetime.utcnow().date)
    txn_name = db.Column(db.String(100), nullable=False)
    account_name = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(8), nullable=False)
    description = db.Column(db.String(500))
    reference_id = db.Column(db.String(25))
    current_balance = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(50))
