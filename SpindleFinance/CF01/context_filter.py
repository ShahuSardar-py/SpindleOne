"""
context_filter.py
-----------------
Why this exists:
    dashboardCalc.get_dashboard_context() returns 30+ keys.
    Sending all of them to LLM on every query is wasteful and
    unfocused. This module maps query intent → relevant key groups,
    so LLM only sees what it needs.

Usage:
    from C_F01.context_filter import filter_context_for_query
    filtered = filter_context_for_query("which invoices are overdue?")
"""

from ..services.dashboardCalc import get_dashboard_context

CONTEXT_GROUPS = {
    "cashflow": [
        "latest_balance",
        "total_inflow",
        "total_outflow",
        "net_cashflow",
        "cashflow_change",
        "inflow_mom_pct",
        "outflow_mom_pct",
        "inflow_count",
        "outflow_count",
        "months",
        "inflows",
        "outflows",
        "nets",
    ],
    "invoice": [
        "total_receivable",
        "total_paid_amount",
        "open_invoices",
        "paid_invoices",
        "overdue_count",
        "overdue_amount",
        "collection_efficiency",
    ],
    "aging": [
        "aging_buckets",
        "aging_counts",
        "aging_max",
        "overdue_count",
        "overdue_amount",
    ],
    "expense": [
        "expense_labels",
        "expense_amounts",
        "expense_pcts",
        "top_expense_category",
        "total_outflow",
    ],
    "client": [
        "top_client_name",
        "top_client_amount",
        "top_clients",
        "concentration_pct",
        "concentration_risk",
    ],
    "source": [
        "source_labels",
        "source_amounts",
        "txn_types",
        "txn_counts",
    ],
    "summary": [
        # Used for general / broad questions — core snapshot only
        "latest_balance",
        "net_cashflow",
        "total_inflow",
        "total_outflow",
        "total_receivable",
        "overdue_count",
        "overdue_amount",
        "collection_efficiency",
        "top_expense_category",
        "concentration_risk",
    ],
}

# ── Keyword → intent mapping ──────────────────────────────────────────────────
INTENT_KEYWORDS = {
    "cashflow":  ["cash", "balance", "inflow", "outflow", "net", "flow", "bank", "month"],
    "invoice":   ["invoice", "paid", "unpaid", "receivable", "collection", "billed"],
    "aging":     ["overdue", "aging", "due", "late", "days", "outstanding", "bucket"],
    "expense":   ["expense", "spend", "cost", "outgoing", "category", "vendor"],
    "client":    ["client", "customer", "concentration", "exposure", "top client"],
    "source":    ["source", "income source", "revenue source", "where", "breakdown"],
}


def _detect_intent(query: str) -> str:
    query_lower = query.lower()
    scores = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)

    # If nothing matched, fall back to summary
    if scores[best_intent] == 0:
        return "summary"

    return best_intent


def filter_context_for_query(query: str) -> dict:
    """
    Main entry point.
    Returns:
        dict with:
            - 'intent'  : detected intent string
            - 'context' : filtered subset of dashboard metrics
    """
    full_context = get_dashboard_context()
    intent = _detect_intent(query)
    relevant_keys = CONTEXT_GROUPS.get(intent, CONTEXT_GROUPS["summary"])

    filtered = {
        key: full_context[key]
        for key in relevant_keys
        if key in full_context
    }

    return {
        "intent": intent,
        "context": filtered,
    }