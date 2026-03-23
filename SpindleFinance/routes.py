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
from .services.transaction_ingestion import ingest_data
from flask import current_app 
from .services.invoice_status import update_invoice_status

@bp.route('/')
def index():
    return redirect(url_for('spindlefinance.dashboard'))

@bp.route('/dashboard')
def dashboard():
    # --- Fetch Data ---
    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    all_invoices = Invoice.query.all()
    today = datetime.utcnow().date()

    # --- Cashflow Core Metrics ---
    total_inflow = sum(c.amount for c in cashflows if c.txn_type == 'INFLOW')
    total_outflow = sum(c.amount for c in cashflows if c.txn_type == 'OUTFLOW')
    net_cashflow = total_inflow - total_outflow

    latest_balance = cashflows[0].current_balance if cashflows else 0
    recent_transactions = cashflows[:5] if cashflows else []

    avg_transaction = (
        sum(c.amount for c in cashflows) / len(cashflows)
        if cashflows else 0
    )

    savings_rate = (
        (net_cashflow / total_inflow) * 100
        if total_inflow > 0 else 0
    )

    # --- Invoice Metrics ---
    total_receivable = sum(
        inv.amt_recievable for inv in all_invoices
        if inv.status.upper() == 'OPEN'
    )

    overdue_count = sum(
        1 for inv in all_invoices
        if inv.status.upper() == 'OPEN' and inv.due_date < today
    )

    overdue_amount = sum(
        inv.amt_recievable for inv in all_invoices
        if inv.status.upper() == 'OPEN' and inv.due_date < today
    )

    paid_invoices = sum(
        1 for inv in all_invoices if inv.status.upper() == 'PAID'
    )

    open_invoices = sum(
        1 for inv in all_invoices if inv.status.upper() == 'OPEN'
    )

    total_paid_amount = sum(
        inv.amt_recievable for inv in all_invoices
        if inv.status.upper() == 'PAID'
    )

    total_invoice_amount = sum(inv.amt_recievable for inv in all_invoices)

    collection_efficiency = (
        (total_paid_amount / total_invoice_amount) * 100
        if total_invoice_amount > 0 else 0
    )

    # --- Monthly Aggregation ---
    monthly_inflows = {}
    monthly_outflows = {}

    for c in cashflows:
        month_key = c.txn_date.strftime('%Y-%m')
        if c.txn_type == 'INFLOW':
            monthly_inflows[month_key] = monthly_inflows.get(month_key, 0) + c.amount
        else:
            monthly_outflows[month_key] = monthly_outflows.get(month_key, 0) + c.amount

    # --- Last 6 Months Data ---
    months = []
    inflows = []
    outflows = []

    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_str = month_date.strftime('%Y-%m')

        months.append(month_date.strftime('%b %Y'))
        inflows.append(monthly_inflows.get(month_str, 0))
        outflows.append(monthly_outflows.get(month_str, 0))

    # --- Cashflow Trend Change (Momentum) ---
    current_month = today.strftime('%Y-%m')
    prev_month = (today - timedelta(days=30)).strftime('%Y-%m')

    current_net = monthly_inflows.get(current_month, 0) - monthly_outflows.get(current_month, 0)
    prev_net = monthly_inflows.get(prev_month, 0) - monthly_outflows.get(prev_month, 0)

    cashflow_change = current_net - prev_net

    # --- Transaction Distribution ---
    inflow_count = sum(1 for c in cashflows if c.txn_type == 'INFLOW')
    outflow_count = sum(1 for c in cashflows if c.txn_type == 'OUTFLOW')

    # --- Top Expense Category ---
    from collections import defaultdict

    expense_categories = defaultdict(float)
    for c in cashflows:
        if c.txn_type == 'OUTFLOW':
            expense_categories[c.account_name] += c.amount

    top_expense_category = (
        max(expense_categories, key=expense_categories.get)
        if expense_categories else None
    )

    # --- Render ---
    return render_template(
        'dashboard.html',

        # Core
        cashflows=cashflows,
        recent_transactions=recent_transactions,
        latest_balance=latest_balance,

        # Cashflow Metrics
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        net_cashflow=net_cashflow,
        cashflow_change=cashflow_change,
        savings_rate=savings_rate,
        avg_transaction=avg_transaction,

        # Invoice Metrics
        total_receivable=total_receivable,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        paid_invoices=paid_invoices,
        open_invoices=open_invoices,
        collection_efficiency=collection_efficiency,

        # Charts
        months=months,
        inflows=inflows,
        outflows=outflows,
        txn_types=['Inflow', 'Outflow'],
        txn_counts=[inflow_count, outflow_count],

        # Insights
        top_expense_category=top_expense_category
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

        # Get invoice_id from form (if provided)
        invoice_id = request.form.get('invoice_id')
        # Convert to int only if it's a non-empty string
        if invoice_id and invoice_id.strip():
            invoice_id = int(invoice_id)
        else:
            invoice_id = None
        
        cashflow = AccountCashflow(
            txn_date=datetime.strptime(request.form['txn_date'], '%Y-%m-%d').date(),
            amount=amount,
            txn_name=request.form['txn_name'],
            account_name=request.form['account_name'],
            txn_type=txn_type,
            description=request.form.get('description', ''),
            reference_id=request.form.get('reference_id', ''),
            current_balance= new_bal,
            source='MANUAL',
            invoice_id=invoice_id
        )

        db.session.add(cashflow)
        db.session.commit()
        
        # Update invoice status after cashflow is saved
        if invoice_id:
            update_invoice_status(invoice_id)

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

    # Update invoice statuses dynamically before returning
    invoices_to_update = Invoice.query.all()
    for inv in invoices_to_update:
        update_invoice_status(inv.inv_id)

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
