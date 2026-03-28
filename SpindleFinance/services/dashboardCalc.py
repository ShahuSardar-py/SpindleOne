"""
dashboard_service.py
--------------------
All heavy-lifting calculations for the Finance Command dashboard.
Call get_dashboard_context() from your route and unpack into render_template().
"""

from collections import defaultdict
from datetime import datetime, timedelta
from ..models import AccountCashflow, Invoice, Client


def get_dashboard_context() -> dict:
    today = datetime.utcnow().date()

    cashflows    = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    all_invoices = Invoice.query.all()

    # ------------------------------------------------------------------ #
    #  Split by type once — reuse everywhere                              #
    # ------------------------------------------------------------------ #
    inflow_txns  = [c for c in cashflows if c.txn_type == 'INFLOW']
    outflow_txns = [c for c in cashflows if c.txn_type == 'OUTFLOW']

    # ------------------------------------------------------------------ #
    #  Core cashflow metrics                                              #
    # ------------------------------------------------------------------ #
    total_inflow  = sum(c.amount for c in inflow_txns)
    total_outflow = sum(c.amount for c in outflow_txns)
    net_cashflow  = total_inflow - total_outflow

    latest_balance      = cashflows[0].current_balance if cashflows else 0
    recent_transactions = cashflows[:5]

    # ------------------------------------------------------------------ #
    #  Monthly aggregation                                                #
    # ------------------------------------------------------------------ #
    monthly_inflows:  dict[str, float] = defaultdict(float)
    monthly_outflows: dict[str, float] = defaultdict(float)

    for c in cashflows:
        key = c.txn_date.strftime('%Y-%m')
        if c.txn_type == 'INFLOW':
            monthly_inflows[key]  += c.amount
        else:
            monthly_outflows[key] += c.amount

    # Last 6 months — labels, inflows, outflows, net (for 3-series chart)
    months:   list[str]   = []
    inflows:  list[float] = []
    outflows: list[float] = []
    nets:     list[float] = []

    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_str  = month_date.strftime('%Y-%m')
        months.append(month_date.strftime('%b %Y'))
        m_in  = monthly_inflows.get(month_str, 0)
        m_out = monthly_outflows.get(month_str, 0)
        inflows.append(m_in)
        outflows.append(m_out)
        nets.append(m_in - m_out)

    # Month-over-month momentum
    current_month = today.strftime('%Y-%m')
    prev_month    = (today - timedelta(days=30)).strftime('%Y-%m')
    current_net   = monthly_inflows[current_month] - monthly_outflows[current_month]
    prev_net      = monthly_inflows[prev_month]    - monthly_outflows[prev_month]
    cashflow_change = current_net - prev_net

    # MoM inflow % change (for KPI badge)
    prev_inflow  = monthly_inflows.get(prev_month, 0)
    curr_inflow  = monthly_inflows.get(current_month, 0)
    inflow_mom_pct = (
        ((curr_inflow - prev_inflow) / prev_inflow) * 100
        if prev_inflow > 0 else 0
    )

    # MoM outflow % change
    prev_outflow = monthly_outflows.get(prev_month, 0)
    curr_outflow = monthly_outflows.get(current_month, 0)
    outflow_mom_pct = (
        ((curr_outflow - prev_outflow) / prev_outflow) * 100
        if prev_outflow > 0 else 0
    )

    # ------------------------------------------------------------------ #
    #  Transaction counts & source mix                                    #
    # ------------------------------------------------------------------ #
    inflow_count  = len(inflow_txns)
    outflow_count = len(outflow_txns)

    # source field breakdown (e.g. 'bank_import', 'manual', 'api')
    source_counts: dict[str, int] = defaultdict(int)
    for c in cashflows:
        label = c.source if c.source else 'Unknown'
        source_counts[label] += 1

    total_txns     = len(cashflows) or 1
    source_labels  = list(source_counts.keys())
    source_amounts = [round((v / total_txns) * 100, 1) for v in source_counts.values()]

    # ------------------------------------------------------------------ #
    #  Expense breakdown by account_name (top 5 for donut)               #
    # ------------------------------------------------------------------ #
    expense_by_category: dict[str, float] = defaultdict(float)
    for c in outflow_txns:
        expense_by_category[c.account_name] += c.amount

    top_expense_category = (
        max(expense_by_category, key=expense_by_category.get)
        if expense_by_category else None
    )

    expense_sorted  = sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[:5]
    expense_labels  = [item[0] for item in expense_sorted]
    expense_amounts = [round(item[1], 2) for item in expense_sorted]

    total_expense = sum(expense_amounts) or 1
    expense_pcts  = [round((v / total_expense) * 100, 1) for v in expense_amounts]

    # ------------------------------------------------------------------ #
    #  Invoice metrics                                                    #
    # ------------------------------------------------------------------ #
    open_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'OPEN']
    paid_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'PAID']

    open_invoices = len(open_invoices_list)
    paid_invoices = len(paid_invoices_list)

    total_receivable     = sum(inv.amt_recievable for inv in open_invoices_list)
    total_paid_amount    = sum(inv.amt_recievable for inv in paid_invoices_list)
    total_invoice_amount = total_receivable + total_paid_amount

    collection_efficiency = (
        (total_paid_amount / total_invoice_amount) * 100
        if total_invoice_amount > 0 else 0
    )

    overdue_list   = [inv for inv in open_invoices_list if inv.due_date < today]
    overdue_count  = len(overdue_list)
    overdue_amount = sum(inv.amt_recievable for inv in overdue_list)

    # ------------------------------------------------------------------ #
    #  Invoice aging buckets                                              #
    #  Negative days_outstanding = not yet due (upcoming)                #
    # ------------------------------------------------------------------ #
    aging_buckets = {'0_30': 0.0, '31_60': 0.0, '61_90': 0.0, '90_plus': 0.0}
    aging_counts  = {'0_30': 0,   '31_60': 0,   '61_90': 0,   '90_plus': 0}

    for inv in open_invoices_list:
        days_outstanding = (today - inv.due_date).days
        amt = inv.amt_recievable
        if days_outstanding <= 30:        # upcoming + 0-30 overdue
            aging_buckets['0_30']   += amt
            aging_counts['0_30']    += 1
        elif days_outstanding <= 60:
            aging_buckets['31_60']  += amt
            aging_counts['31_60']   += 1
        elif days_outstanding <= 90:
            aging_buckets['61_90']  += amt
            aging_counts['61_90']   += 1
        else:
            aging_buckets['90_plus'] += amt
            aging_counts['90_plus']  += 1

    aging_max = max(aging_buckets.values()) or 1  # for bar-width % in template

    # ------------------------------------------------------------------ #
    #  Client exposure & concentration risk                               #
    # ------------------------------------------------------------------ #
    client_receivables: dict[int, float] = defaultdict(float)
    for inv in open_invoices_list:
        client_receivables[inv.client_id] += inv.amt_recievable

    top_client_id     = max(client_receivables, key=client_receivables.get) if client_receivables else None
    top_client        = Client.query.get(top_client_id) if top_client_id else None
    top_client_name   = top_client.name if top_client else None
    top_client_amount = client_receivables.get(top_client_id, 0)

    # Top 5 clients ranked — each is a dict for easy template iteration
    client_ids_ranked = sorted(client_receivables, key=client_receivables.get, reverse=True)[:5]
    max_client_amt    = client_receivables[client_ids_ranked[0]] if client_ids_ranked else 1
    top_clients = []
    for cid in client_ids_ranked:
        client_obj = Client.query.get(cid)
        amt = client_receivables[cid]
        top_clients.append({
            'name':    client_obj.name if client_obj else f'Client #{cid}',
            'amount':  amt,
            'pct':     round((amt / total_receivable) * 100, 1) if total_receivable > 0 else 0,
            'bar_pct': round((amt / max_client_amt) * 100, 1),
        })

    concentration_pct = (
        round((top_client_amount / total_receivable) * 100, 1)
        if total_receivable > 0 else 0
    )
    if concentration_pct >= 80:
        concentration_risk = 'high'
    elif concentration_pct >= 50:
        concentration_risk = 'medium'
    else:
        concentration_risk = 'low'

    # ------------------------------------------------------------------ #
    #  Return full context dict                                           #
    # ------------------------------------------------------------------ #
    return dict(
        # ── Raw data ──────────────────────────────────────────────────
        cashflows=cashflows,
        recent_transactions=recent_transactions,
        all_invoices=all_invoices,
        open_invoices_list=open_invoices_list,
        today=today,

        # ── Core cashflow ─────────────────────────────────────────────
        latest_balance=latest_balance,
        total_inflow=total_inflow,
        total_outflow=total_outflow,
        net_cashflow=net_cashflow,
        cashflow_change=cashflow_change,
        inflow_mom_pct=round(inflow_mom_pct, 1),
        outflow_mom_pct=round(outflow_mom_pct, 1),

        # ── Transaction counts ────────────────────────────────────────
        inflow_count=inflow_count,
        outflow_count=outflow_count,
        txn_types=['Inflow', 'Outflow'],
        txn_counts=[inflow_count, outflow_count],

        # ── Source mix ────────────────────────────────────────────────
        source_labels=source_labels,
        source_amounts=source_amounts,   # list of percentages

        # ── Expense breakdown ─────────────────────────────────────────
        expense_labels=expense_labels,
        expense_amounts=expense_amounts,
        expense_pcts=expense_pcts,
        top_expense_category=top_expense_category,

        # ── Invoice metrics ───────────────────────────────────────────
        total_receivable=total_receivable,
        total_paid_amount=total_paid_amount,
        open_invoices=open_invoices,
        paid_invoices=paid_invoices,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        collection_efficiency=round(collection_efficiency, 1),

        # ── Invoice aging ─────────────────────────────────────────────
        aging_buckets=aging_buckets,
        aging_counts=aging_counts,
        aging_max=aging_max,

        # ── Client exposure ───────────────────────────────────────────
        top_client_name=top_client_name,
        top_client_amount=top_client_amount,
        top_clients=top_clients,
        concentration_pct=concentration_pct,
        concentration_risk=concentration_risk,

        # ── Chart series (JSON-safe) ──────────────────────────────────
        months=months,
        inflows=inflows,
        outflows=outflows,
        nets=nets,
    )