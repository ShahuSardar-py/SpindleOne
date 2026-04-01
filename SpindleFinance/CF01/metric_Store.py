"""
metric_store.py
---------------
Single source of truth for all financial metrics.

Dumps dashboardCalc.get_dashboard_context() into a clean,
LLM-readable JSON store — stripping ORM objects, coercing
types, and caching with a TTL so the LLM always has fresh
but not redundantly fetched data.

The store is what the LLM reads. It never touches raw DB objects.

Usage:
    from CF01.metric_store import get_metric_store, refresh_store
    store = get_metric_store()   # returns cached or fresh JSON string
"""

import json
import math
import threading
from datetime import date, datetime, timezone
from decimal import Decimal

from ..services.dashboardCalc import get_dashboard_context


# ── Config ────────────────────────────────────────────────────────────────────

# How long (seconds) before the store is considered stale and refreshed
STORE_TTL_SECONDS = 120   # 2 minutes — tune to your traffic

# Keys from dashboardCalc that are ORM object lists — always excluded
ORM_KEYS = {
    "cashflows",
    "all_invoices",
    "open_invoices_list",
    "recent_transactions",
    "today",               # handled separately as metadata
}


# ── In-memory cache ───────────────────────────────────────────────────────────

_cache = {
    "store":      None,    # the JSON string
    "built_at":   None,    # datetime the store was last built
    "lock":       threading.Lock(),
}


# ── Type coercion ─────────────────────────────────────────────────────────────

def _coerce(value):
    """
    Recursively makes any value JSON-serializable.
    Handles Decimal, date, datetime, float inf/nan, nested dicts/lists.
    """
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0
        return round(value, 4)

    if isinstance(value, dict):
        return {k: _coerce(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_coerce(i) for i in value]

    return value


# ── Store builder ─────────────────────────────────────────────────────────────

def _build_store() -> str:
    """
    Fetches dashboardCalc context, strips ORM keys,
    coerces all types, and returns a formatted JSON string.

    The JSON is structured into named sections so the LLM
    can navigate it semantically rather than scanning a flat dict.
    """
    raw = get_dashboard_context()

    # ── Strip ORM keys ────────────────────────────────────────────────────────
    clean = {k: v for k, v in raw.items() if k not in ORM_KEYS}

    # ── Coerce all types ──────────────────────────────────────────────────────
    clean = _coerce(clean)

    # ── Structure into named sections for LLM readability ────────────────────
    store = {
        "_meta": {
            "built_at":   datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": STORE_TTL_SECONDS,
            "currency":   "INR",
            "note":       "All amounts in INR. Percentages are 0-100 scale.",
        },

        "cashflow": {
            "latest_balance":   clean.get("latest_balance", 0),
            "total_inflow":     clean.get("total_inflow", 0),
            "total_outflow":    clean.get("total_outflow", 0),
            "net_cashflow":     clean.get("net_cashflow", 0),
            "cashflow_change":  clean.get("cashflow_change", 0),
            "inflow_mom_pct":   clean.get("inflow_mom_pct", 0),
            "outflow_mom_pct":  clean.get("outflow_mom_pct", 0),
            "inflow_count":     clean.get("inflow_count", 0),
            "outflow_count":    clean.get("outflow_count", 0),
        },

        "trend": {
            "months":   clean.get("months", []),
            "inflows":  clean.get("inflows", []),
            "outflows": clean.get("outflows", []),
            "nets":     clean.get("nets", []),
        },

        "invoices": {
            "total_receivable":     clean.get("total_receivable", 0),
            "total_paid_amount":    clean.get("total_paid_amount", 0),
            "open_invoices":        clean.get("open_invoices", 0),
            "paid_invoices":        clean.get("paid_invoices", 0),
            "overdue_count":        clean.get("overdue_count", 0),
            "overdue_amount":       clean.get("overdue_amount", 0),
            "collection_efficiency": clean.get("collection_efficiency", 0),
        },

        "aging": {
            "buckets": clean.get("aging_buckets", {}),
            "counts":  clean.get("aging_counts", {}),
            "max":     clean.get("aging_max", 0),
        },

        "expenses": {
            "labels":           clean.get("expense_labels", []),
            "amounts":          clean.get("expense_amounts", []),
            "percentages":      clean.get("expense_pcts", []),
            "top_category":     clean.get("top_expense_category", "N/A"),
        },

        "clients": {
            "top_client_name":   clean.get("top_client_name", "N/A"),
            "top_client_amount": clean.get("top_client_amount", 0),
            "top_clients":       clean.get("top_clients", []),
            "concentration_pct": clean.get("concentration_pct", 0),
            "concentration_risk": clean.get("concentration_risk", "low"),
        },

        "sources": {
            "labels":  clean.get("source_labels", []),
            "amounts": clean.get("source_amounts", []),
            "txn_types":  clean.get("txn_types", []),
            "txn_counts": clean.get("txn_counts", []),
        },
    }

    return json.dumps(store, indent=2)


# ── TTL check ─────────────────────────────────────────────────────────────────

def _is_stale() -> bool:
    if _cache["built_at"] is None:
        return True
    delta = (datetime.now(timezone.utc) - _cache["built_at"]).total_seconds()
    return delta > STORE_TTL_SECONDS


# ── Public API ────────────────────────────────────────────────────────────────

def get_metric_store(force_refresh: bool = False) -> str:
    """
    Returns the metric store as a JSON string.
    Uses cached version if within TTL, refreshes if stale.

    Args:
        force_refresh: If True, bypasses TTL and rebuilds immediately.

    Returns:
        JSON string of the full metric store.
    """
    with _cache["lock"]:
        if force_refresh or _is_stale():
            _cache["store"]    = _build_store()
            _cache["built_at"] = datetime.now(timezone.utc)

    return _cache["store"]


def refresh_store() -> str:
    """
    Force rebuilds the store immediately.
    Call this after new transactions are recorded.

    Returns:
        Fresh JSON string.
    """
    return get_metric_store(force_refresh=True)


def get_store_age_seconds() -> float | None:
    """
    Returns how old the current cache is in seconds.
    Returns None if store has never been built.
    """
    if _cache["built_at"] is None:
        return None
    return (datetime.now(timezone.utc) - _cache["built_at"]).total_seconds()