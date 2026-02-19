from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from .models import AccountCashflow, Invoice, Client
from datetime import datetime, timedelta
from . import bp
from flask import jsonify
import os
from werkzeug.utils import secure_filename
from flask import flash
from .services.transaction_ingestion import get_balance

@bp.route('/')
def index():
    return redirect(url_for('spindlefinance.dashboard'))

@bp.route('/dashboard')
def dashboard():
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    
    total_inflow = sum(c.amount for c in cashflows if c.txn_type == 'INFLOW')
    total_outflow = sum(c.amount for c in cashflows if c.txn_type == 'OUTFLOW')
    
    latest_balance = cashflows[0].current_balance if cashflows else 0
    
    recent_transactions = cashflows[:5] if cashflows else []
    
    monthly_inflows = {}
    monthly_outflows = {}
    
    for c in cashflows:
        month_key = c.txn_date.strftime('%Y-%m')
        if c.txn_type == 'INFLOW':
            monthly_inflows[month_key] = monthly_inflows.get(month_key, 0) + c.amount
        else:
            monthly_outflows[month_key] = monthly_outflows.get(month_key, 0) + c.amount
    
    all_months = sorted(set(monthly_inflows.keys()) | set(monthly_outflows.keys()))
    
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
        amount = float(request.form['amount'])
        txn_type = request.form['txn_type']
        
        current_bal = get_balance()

        if txn_type == 'INFLOW':
            new_bal = current_bal + amount
        else:
            new_bal = current_bal - amount

        
        cashflow = AccountCashflow(
            txn_date=datetime.strptime(request.form['txn_date'], '%Y-%m-%d').date(),
            amount=amount,
            txn_name=request.form['txn_name'],
            account_name=request.form['account_name'],
            txn_type=txn_type,
            description=request.form.get('description', ''),
            reference_id=request.form.get('reference_id', ''),
            current_balance= new_bal,
            source='MANUAL'
        )
        db.session.add(cashflow)
        db.session.commit()
        return redirect(url_for('spindlefinance.cashflow'))
        # Pass invoices joined with client name for the dropdown
    invoices = (
        db.session.query(Invoice, Client)
        .join(Client, Invoice.client_id == Client.id)
        .order_by(Invoice.inv_id.desc())
        .all()
    )
    return render_template('addRecord.html', invoices=invoices)

@bp.route('/records')
def records():
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    return render_template('records.html', cashflows=cashflows)

from .services.transaction_ingestion import ingest_data
from flask import current_app 
@bp.route('/upload', methods=['POST'])
def uploader():
    file= request.files.get('file')
    if not file:
        return {"error": "No file"}, 400
    filename = secure_filename(file.filename)

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    file.save(path)

    try:
        count = ingest_data(path)
    except Exception as e:
        current_app.logger.exception(e)
        return {"error": str(e)}, 400

    return {"inserted": count}


@bp.route('/receivables')
def receivables():
    return render_template('receivables.html')

@bp.route("/clients", methods=["POST"])
def add_client():

    data = request.get_json()

    client = Client(
        name=data["name"],
        contact_info=data.get("contact_info")
    )

    db.session.add(client)
    db.session.commit()

    return jsonify({"message": "Client created", "client_id": client.id}), 201

@bp.route("/clients", methods=["GET"])
def list_clients():

    clients = Client.query.order_by(Client.created_at.desc()).all()

    result = []
    for c in clients:
        result.append({
            "client_id": c.id,
            "name": c.name,
            "contact_info": c.contact_info,
            "created_at": c.created_at
        })

    return jsonify(result)

@bp.route("/invoices", methods=["POST"])
def add_invoice():

    data = request.get_json()

    # basic safety check
    client = Client.query.get(data["client_id"])
    if not client:
        return jsonify({"error": "Client not found"}), 404

    invoice = Invoice(
        client_id=data["client_id"],
        product_name=data["product_name"],
        amt_recievable=data["amt_recievable"],
        due_date=datetime.strptime(data["due_date"], "%Y-%m-%d").date(),
        status=data.get("status", "OPEN")
    )

    db.session.add(invoice)
    db.session.commit()

    return jsonify({"message": "Invoice created", "invoice_id": invoice.inv_id}), 201

@bp.route("/invoices", methods=["GET"])
def list_invoices():

    invoices = (
        db.session.query(Invoice, Client)
        .join(Client, Invoice.client_id == Client.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )

    result = []

    for inv, client in invoices:
        result.append({
            "invoice_id": inv.inv_id,
            "client_id": client.id,
            "client_name": client.name,
            "product_name": inv.product_name,
            "amt_recievable": inv.amt_recievable,
            "due_date": inv.due_date,
            "status": inv.status,
            "created_at": inv.created_at
        })

    return jsonify(result)
