from collections import defaultdict
from datetime import datetime, timedelta
from ..models import AccountCashflow, Invoice, Client


def get_dashboard_context() -> dict:
    today = datetime.utcnow().date()

    cashflows = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    all_invoices = Invoice.query.all()

    #  Cashflow Core Metrics                                               #
    inflow_txns  = [c for c in cashflows if c.txn_type == 'INFLOW']
    outflow_txns = [c for c in cashflows if c.txn_type == 'OUTFLOW']

    total_inflow  = sum(c.amount for c in inflow_txns)
    total_outflow = sum(c.amount for c in outflow_txns)
    net_cashflow  = total_inflow - total_outflow

    latest_balance      = cashflows[0].current_balance if cashflows else 0
    recent_transactions = cashflows[:5]

    avg_transaction = (
        sum(c.amount for c in cashflows) / len(cashflows)
        if cashflows else 0
    )

    savings_rate = (
        (net_cashflow / total_inflow) * 100
        if total_inflow > 0 else 0
    )


    #  Monthly Aggregation (used by charts + momentum)                    #
    monthly_inflows:  dict[str, float] = defaultdict(float)
    monthly_outflows: dict[str, float] = defaultdict(float)

    for c in cashflows:
        key = c.txn_date.strftime('%Y-%m')
        if c.txn_type == 'INFLOW':
            monthly_inflows[key]  += c.amount
        else:
            monthly_outflows[key] += c.amount

    months:   list[str]   = []
    inflows:  list[float] = []
    outflows: list[float] = []

    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_str  = month_date.strftime('%Y-%m')
        months.append(month_date.strftime('%b %Y'))
        inflows.append(monthly_inflows.get(month_str, 0))
        outflows.append(monthly_outflows.get(month_str, 0))

    # Month-over-month cashflow momentum
    current_month = today.strftime('%Y-%m')
    prev_month    = (today - timedelta(days=30)).strftime('%Y-%m')
    current_net   = monthly_inflows[current_month] - monthly_outflows[current_month]
    prev_net      = monthly_inflows[prev_month]    - monthly_outflows[prev_month]
    cashflow_change = current_net - prev_net

    #  Transaction Distribution                                           #
    # ------------------------------------------------------------------ #
    inflow_count  = len(inflow_txns)
    outflow_count = len(outflow_txns)

    #  Expense Breakdown by Account/Category                              #
    # ------------------------------------------------------------------ #
    expense_by_category: dict[str, float] = defaultdict(float)
    for c in outflow_txns:
        expense_by_category[c.account_name] += c.amount

    top_expense_category = (
        max(expense_by_category, key=expense_by_category.get)
        if expense_by_category else None
    )

    # Sorted list for a breakdown chart (top 5)
    expense_breakdown = sorted(
        expense_by_category.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    expense_labels  = [item[0] for item in expense_breakdown]
    expense_amounts = [item[1] for item in expense_breakdown]

    #  Invoice Metrics                                                    #
    # ------------------------------------------------------------------ #
    open_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'OPEN']
    paid_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'PAID']

    open_invoices  = len(open_invoices_list)
    paid_invoices  = len(paid_invoices_list)

    total_receivable   = sum(inv.amt_recievable for inv in open_invoices_list)
    total_paid_amount  = sum(inv.amt_recievable for inv in paid_invoices_list)
    total_invoice_amount = total_receivable + total_paid_amount

    overdue_list   = [inv for inv in open_invoices_list if inv.due_date < today]
    overdue_count  = len(overdue_list)
    overdue_amount = sum(inv.amt_recievable for inv in overdue_list)

    collection_efficiency = (
        (total_paid_amount / total_invoice_amount) * 100
        if total_invoice_amount > 0 else 0
    )

    # ------------------------------------------------------------------ #
    #  Top Client by Outstanding Receivables                              #

    client_receivables: dict[int, float] = defaultdict(float)
    for inv in open_invoices_list:
        client_receivables[inv.client_id] += inv.amt_recievable

    top_client_id     = max(client_receivables, key=client_receivables.get) if client_receivables else None
    top_client        = Client.query.get(top_client_id) if top_client_id else None
    top_client_name   = top_client.name if top_client else None
    top_client_amount = client_receivables.get(top_client_id, 0)

    #  Return flat context dict                                           #
    # ------------------------------------------------------------------ #
    return dict(
        # Raw data (for table rendering)
        cashflows=cashflows,
        recent_transactions=recent_transactions,

        # Cashflow metrics
        latest_balance=latest_balance,
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        net_cashflow=net_cashflow,
        cashflow_change=cashflow_change,
        savings_rate=savings_rate,
        avg_transaction=avg_transaction,

        # Invoice metrics
        total_receivable=total_receivable,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        paid_invoices=paid_invoices,
        open_invoices=open_invoices,
        collection_efficiency=collection_efficiency,

        # Top client insight
        top_client_name=top_client_name,
        top_client_amount=top_client_amount,

        # Chart: monthly cashflow (bar/line)
        months=months,
        inflows=inflows,
        outflows=outflows,

        # Chart: inflow vs outflow donut
        txn_types=['Inflow', 'Outflow'],
        txn_counts=[inflow_count, outflow_count],

        # Chart: expense category breakdown (horizontal bar)
        expense_labels=expense_labels,
        expense_amounts=expense_amounts,

        # Insights
        top_expense_category=top_expense_category,
    )