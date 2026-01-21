from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from .models import AccountCashflow
from datetime import datetime
from . import bp

@bp.route('/add', methods=['GET', 'POST'])
def cashflow():
    if request.method == 'POST':
        # Hardcoded starting balance
        starting_balance = 10000.00
        amount = float(request.form['amount'])
        txn_type = request.form['txn_type']
        
        new_balance = starting_balance + amount if txn_type == 'INFLOW' else starting_balance - amount
        
        cashflow = AccountCashflow(
            txn_date=datetime.strptime(request.form['txn_date'], '%Y-%m-%d').date(),
            amount=amount,
            txn_name=request.form['txn_name'],
            account_name=request.form['account_name'],
            txn_type=txn_type,
            description=request.form.get('description', ''),
            reference_id=request.form.get('reference_id', ''),
            current_balance=new_balance,
            source='MANUAL'
        )
        db.session.add(cashflow)
        db.session.commit()
        return redirect(url_for('spindlefinance.records'))
    return render_template('addRecord.html')

@bp.route('/records')
def records():
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    return render_template('records.html', cashflows=cashflows)
