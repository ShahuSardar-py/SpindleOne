from collections import defaultdict
from datetime import datetime, timedelta
from ..models import AccountCashflow, Invoice, Client

#  Helpers                                                            #
def _safe_pct(numerator: float, denominator: float, ndigits: int = 1) -> float:
    """Return (numerator / denominator * 100) rounded to ndigits, or 0.0."""
    return round((numerator / denominator) * 100, ndigits) if denominator else 0.0


def _safe_div(numerator: float, denominator: float, ndigits: int = 1) -> float:
    """Return (numerator / denominator) rounded to ndigits, or 0.0."""
    return round(numerator / denominator, ndigits) if denominator else 0.0


#  Main entry point                                                   #
def get_dashboard_context() -> dict:
    today = datetime.utcnow().date()

    cashflows    = AccountCashflow.query.order_by(AccountCashflow.txn_date.desc()).all()
    all_invoices = Invoice.query.all()

    #  Split by type once — reuse everywhere                              #
    inflow_txns  = [c for c in cashflows if c.txn_type == 'INFLOW']
    outflow_txns = [c for c in cashflows if c.txn_type == 'OUTFLOW']

    #  Core cashflow metrics                                              #
    total_inflow  = sum(c.amount for c in inflow_txns)
    total_outflow = sum(c.amount for c in outflow_txns)
    net_cashflow  = total_inflow - total_outflow

    latest_balance      = cashflows[0].current_balance if cashflows else 0.0
    recent_transactions = cashflows[:5]

    #  Monthly aggregation                                                #
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
        m_in  = monthly_inflows.get(month_str, 0.0)
        m_out = monthly_outflows.get(month_str, 0.0)
        inflows.append(m_in)
        outflows.append(m_out)
        nets.append(m_in - m_out)

    # Month-over-month momentum
    current_month = today.strftime('%Y-%m')
    prev_month    = (today - timedelta(days=30)).strftime('%Y-%m')

    curr_in  = monthly_inflows.get(current_month, 0.0)
    prev_in  = monthly_inflows.get(prev_month, 0.0)
    curr_out = monthly_outflows.get(current_month, 0.0)
    prev_out = monthly_outflows.get(prev_month, 0.0)

    current_net     = curr_in  - curr_out
    prev_net        = prev_in  - prev_out
    cashflow_change = current_net - prev_net

    # MoM % changes — fully guarded
    inflow_mom_pct  = _safe_pct(curr_in  - prev_in,  prev_in)
    outflow_mom_pct = _safe_pct(curr_out - prev_out, prev_out)

    #  Transaction counts & source mix                                    #
    inflow_count  = len(inflow_txns)
    outflow_count = len(outflow_txns)
    total_txns    = len(cashflows)  # may be 0

    source_counts: dict[str, int] = defaultdict(int)
    for c in cashflows:
        label = c.source if c.source else 'Unknown'
        source_counts[label] += 1

    source_labels  = list(source_counts.keys())
    source_amounts = [_safe_pct(v, total_txns) for v in source_counts.values()]

    #  Expense breakdown by account_name (top 5 for donut)               #
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
    total_expense   = sum(expense_amounts)

    expense_pcts = [_safe_pct(v, total_expense) for v in expense_amounts]

    #  Invoice metrics                                                    #
    open_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'OPEN']
    paid_invoices_list = [inv for inv in all_invoices if inv.status.upper() == 'PAID']

    open_invoices = len(open_invoices_list)
    paid_invoices = len(paid_invoices_list)

    total_receivable     = sum(inv.amt_recievable for inv in open_invoices_list)
    total_paid_amount    = sum(inv.amt_recievable for inv in paid_invoices_list)
    total_invoice_amount = total_receivable + total_paid_amount

    collection_efficiency = _safe_pct(total_paid_amount, total_invoice_amount)

    overdue_list   = [inv for inv in open_invoices_list if inv.due_date < today]
    overdue_count  = len(overdue_list)
    overdue_amount = sum(inv.amt_recievable for inv in overdue_list)

    #  Invoice aging buckets                                              #
    #  Negative days_outstanding = not yet due (upcoming)                #
    aging_buckets: dict[str, float] = {'0_30': 0.0, '31_60': 0.0, '61_90': 0.0, '90_plus': 0.0}
    aging_counts:  dict[str, int]   = {'0_30': 0,   '31_60': 0,   '61_90': 0,   '90_plus': 0}

    for inv in open_invoices_list:
        days_outstanding = (today - inv.due_date).days
        amt = inv.amt_recievable
        if days_outstanding <= 30:
            aging_buckets['0_30']    += amt
            aging_counts['0_30']     += 1
        elif days_outstanding <= 60:
            aging_buckets['31_60']   += amt
            aging_counts['31_60']    += 1
        elif days_outstanding <= 90:
            aging_buckets['61_90']   += amt
            aging_counts['61_90']    += 1
        else:
            aging_buckets['90_plus'] += amt
            aging_counts['90_plus']  += 1

    aging_max = max(aging_buckets.values()) or 1.0  # for bar-width % in template

    #  Client exposure & concentration risk                               #
    client_receivables: dict[int, float] = defaultdict(float)
    for inv in open_invoices_list:
        client_receivables[inv.client_id] += inv.amt_recievable

    if client_receivables:
        top_client_id = max(client_receivables, key=client_receivables.get)
        top_client    = Client.query.get(top_client_id)
    else:
        top_client_id = None
        top_client    = None

    top_client_name   = top_client.name if top_client else None
    top_client_amount = client_receivables.get(top_client_id, 0.0) if top_client_id is not None else 0.0

    # Top 5 clients ranked
    client_ids_ranked = sorted(client_receivables, key=client_receivables.get, reverse=True)[:5]
    max_client_amt    = client_receivables[client_ids_ranked[0]] if client_ids_ranked else 0.0

    top_clients = []
    for cid in client_ids_ranked:
        client_obj = Client.query.get(cid)
        amt = client_receivables[cid]
        top_clients.append({
            'name':    client_obj.name if client_obj else f'Client #{cid}',
            'amount':  amt,
            'pct':     _safe_pct(amt, total_receivable),
            'bar_pct': _safe_pct(amt, max_client_amt),
        })

    concentration_pct = _safe_pct(top_client_amount, total_receivable)
    if concentration_pct >= 80:
        concentration_risk = 'high'
    elif concentration_pct >= 50:
        concentration_risk = 'medium'
    else:
        concentration_risk = 'low'

    #  Return full context dict                                           #
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
        collection_efficiency=collection_efficiency,

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