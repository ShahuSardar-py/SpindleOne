from datetime import date
from sqlalchemy import func
from app.extensions import db
from ..models import Invoice, AccountCashflow

def update_invoice_status(inv_id: int):
    invoice = Invoice.query.get(inv_id)
    if not invoice:
        return

    total_paid = (
        db.session.query(func.coalesce(func.sum(AccountCashflow.amount), 0))
        .filter(
            AccountCashflow.invoice_id == inv_id,
            AccountCashflow.txn_type == "INFLOW"
        )
        .scalar()
    )

    today = date.today()

    if total_paid >= invoice.amt_recievable:
        new_status = "PAID"
    elif total_paid > 0:
        # Has at least one installment, but not fully settled
        if today > invoice.due_date:
            new_status = "OVERDUE"   # still overdue — partial doesn't excuse lateness
        else:
            new_status = "PARTIAL"
    else:
        if today > invoice.due_date:
            new_status = "OVERDUE"
        else:
            new_status = "OPEN"

    if invoice.status != new_status:
        invoice.status = new_status
        db.session.commit()