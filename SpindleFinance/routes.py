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
            "due_date":        str(inv.due_date) if inv.due_date else None,
            "status":          inv.status,
            "created_at":      str(inv.created_at) if inv.created_at else None,
            "total_paid":      total_paid,
            "pct_paid":        pct_paid,
        })

    return jsonify(result)
