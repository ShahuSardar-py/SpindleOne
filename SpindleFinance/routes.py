from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from .models import AccountCashflow
from datetime import datetime, timedelta
from . import bp

@bp.route('/')
def index():
    return redirect(url_for('spindlefinance.dashboard'))

@bp.route('/dashboard')
def dashboard():
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    
    # Calculate summary statistics
    total_inflow = sum(c.amount for c in cashflows if c.txn_type == 'INFLOW')
    total_outflow = sum(c.amount for c in cashflows if c.txn_type == 'OUTFLOW')
    
    # Get latest balance
    latest_balance = cashflows[0].current_balance if cashflows else 0
    
    # Get recent transactions (last 5)
    recent_transactions = cashflows[:5] if cashflows else []
    
    # Group by month manually for charts
    monthly_inflows = {}
    monthly_outflows = {}
    
    for c in cashflows:
        month_key = c.txn_date.strftime('%Y-%m')
        if c.txn_type == 'INFLOW':
            monthly_inflows[month_key] = monthly_inflows.get(month_key, 0) + c.amount
        else:
            monthly_outflows[month_key] = monthly_outflows.get(month_key, 0) + c.amount
    
    # Get all unique months and sort them
    all_months = sorted(set(monthly_inflows.keys()) | set(monthly_outflows.keys()))
    
    # Get last 6 months for display
    six_months_data = []
    for i in range(5, -1, -1):
        d = datetime.utcnow().date() - timedelta(days=30 * i)
        six_months_data.append(d.strftime('%Y-%m'))
    six_months_data = list(dict.fromkeys(six_months_data))
    
    months = []
    inflows = []
    outflows = []
    
    for m in six_months_data[:6]:
        months.append(m)
        inflows.append(monthly_inflows.get(m, 0))
        outflows.append(monthly_outflows.get(m, 0))
    
    # Transaction type distribution
    inflow_count = sum(1 for c in cashflows if c.txn_type == 'INFLOW')
    outflow_count = sum(1 for c in cashflows if c.txn_type == 'OUTFLOW')
    
    txn_types = ['INFLOW', 'OUTFLOW'] if cashflows else []
    txn_counts = [inflow_count, outflow_count]
    
    return render_template(
        'dashboard.html',
        cashflows=cashflows,
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        latest_balance=latest_balance,
        recent_transactions=recent_transactions,
        months=months,
        inflows=inflows,
        outflows=outflows,
        txn_types=txn_types,
        txn_counts=txn_counts
    )

@bp.route('/add', methods=['GET', 'POST'])
def cashflow():
    if request.method == 'POST':
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
        return redirect(url_for('spindlefinance.cashflow'))
    return render_template('addRecord.html')

@bp.route('/records')
def records():
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    return render_template('records.html', cashflows=cashflows)

