from flask import Blueprint, render_template, request, redirect, url_for
from app.extensions import db
from .models import AccountCashflow, Invoice, Client
from datetime import datetime, timedelta
from . import bp
from flask import jsonify
import os
from werkzeug.utils import secure_filename
from flask import Flask
from .services.transaction_ingestion import get_balance
from .services.transaction_ingestion import ingest_data
from flask import current_app 
from .services.invoice_status import update_invoice_status
from .services.dashboardCalc import get_dashboard_context
from .CF01.chat import chat 
from sqlalchemy import func


@bp.route('/')
def index():
    return redirect(url_for('spindlefinance.dashboard'))

@bp.route('/dashboard')
def dashboard():
    context = get_dashboard_context()
    return render_template('Financedashboard.html', **context)
 

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
        
        sale_type = request.form.get('sale_type')
        if txn_type != 'INFLOW':
            sale_type = None

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
            invoice_id=invoice_id,
            sale_type=sale_type
        )

        db.session.add(cashflow)
        db.session.commit()
        
        from .CF01.metric_Store import refresh_store
        try:
            refresh_store()
        except Exception:
            pass

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

from sqlalchemy.orm import joinedload

@bp.route('/records')
def records():
    cashflows = (
        AccountCashflow.query
        .options(joinedload(AccountCashflow.invoice))  # assumes relationship exists
        .order_by(AccountCashflow.txn_date.desc())
        .all()
    )
    # Annotate each inflow with a late flag at the Python level
    for cf in cashflows:
        cf.is_late_payment = (
            cf.txn_type == 'INFLOW'
            and cf.invoice is not None
            and cf.invoice.due_date is not None
            and cf.txn_date is not None
            and cf.txn_date > cf.invoice.due_date
        )
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

    gst_rate = float(data.get("gst_rate") or 0.0)
    base_amount = float(data["amt_recievable"])
    total_payable = base_amount * (1 + gst_rate / 100)

    invoice = Invoice(
        client_id=data["client_id"],
        product_name=data["product_name"],
        amt_recievable=total_payable,
        due_date=datetime.strptime(data["due_date"], "%Y-%m-%d").date(),
        status=data.get("status", "OPEN"),
        gst_rate=gst_rate
    )

    db.session.add(invoice)
    db.session.commit()

    return jsonify({"message": "Invoice created", "invoice_id": invoice.inv_id}), 201

@bp.route("/chat", methods=["POST"])
def chat_api():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    result = chat(query)
    return jsonify(result)

@bp.route("/invoices", methods=["GET"])
def list_invoices():

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
        total_paid = (
            db.session.query(func.coalesce(func.sum(AccountCashflow.amount), 0))
            .filter(
                AccountCashflow.invoice_id == inv.inv_id,
                AccountCashflow.txn_type == "INFLOW"
            )
            .scalar()
        )
        total_paid = float(total_paid)
        amt = float(inv.amt_recievable) if inv.amt_recievable else 0.0
        pct_paid = round((total_paid / amt) * 100, 1) if amt > 0 else 0.0

        result.append({
            "invoice_id":      inv.inv_id,
            "client_id":       client.id,
            "client_name":     client.name,
            "product_name":    inv.product_name,
            "amt_recievable":  amt,
            "gst_rate":        inv.gst_rate or 0.0,
            "due_date":        str(inv.due_date) if inv.due_date else None,
            "status":          inv.status,
            "created_at":      str(inv.created_at) if inv.created_at else None,
            "total_paid":      total_paid,
            "pct_paid":        pct_paid,
        })

    return jsonify(result)


@bp.route('/template/download')
def download_template():
    import csv
    from io import StringIO
    from flask import Response
    
    si = StringIO()
    cw = csv.writer(si)
    # Header row
    cw.writerow([
        'txn_date', 'amount', 'txn_type', 'txn_name', 'account_name', 
        'invoice_id', 'reference_id', 'description', 'sale_type'
    ])
    # Corporate sales example
    cw.writerow([
        '2026-06-21', '125000.00', 'INFLOW', 'Acme Corp Q2 Payment', 'Business Checking',
        '101', '', 'Direct corporate sales invoice settlement', 'Corporate sales'
    ])
    # Outflow example (does not have sale type)
    cw.writerow([
        '2026-06-21', '1500.00', 'OUTFLOW', 'Office Stationaries', 'Petty Cash',
        '', 'REF-9092', 'Paper, pens, and printer cartridges', ''
    ])
    # General Sale example
    cw.writerow([
        '2026-06-21', '45000.00', 'INFLOW', 'General retail sales walk-in', 'Business Checking',
        '', '', 'Walk-in cash counter sale', 'General Sale'
    ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=spindle_finance_template.csv"}
    )
