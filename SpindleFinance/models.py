from datetime import datetime
from app.extensions import db 



#clinet --> invoice is ONE TO MANY. 

#cleint
class Client(db.Model):
    __tablename__ = 'clients'


    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(100), nullable=False)
    #invoice_id= db.Column(db.String(50), nullable= False)--wrong 
    contact_info= db.Column(db.Integer, nullable= True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#invoices
class Invoice(db.Model):
    __tablename__= 'Invoice'

    inv_id= db.Column(db.Integer, primary_key= True)
    client_id = db.Column(db.Integer,db.ForeignKey('clients.id'),
        nullable=False
    )
    product_name = db.Column(db.String(100), nullable=False)
    amt_recievable = db.Column(db.Float, nullable= False)
    due_date = db.Column(db.Date, nullable = False)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.Date, nullable= False, default=datetime.utcnow)
    



#in and out model
class AccountCashflow(db.Model):
    __tablename__ ='AccountCashflow'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey('Invoice.inv_id'),
        nullable=True
    )
    txn_date = db.Column(db.Date, default=datetime.utcnow().date)
    txn_name = db.Column(db.String(100), nullable=False)
    account_name = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(8), nullable=False)
    description = db.Column(db.String(500))
    reference_id = db.Column(db.String(25))
    current_balance = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(50))
    