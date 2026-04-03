"""
validator.py
------------
Final safety check before filtered context reaches Claude.

Responsibilities:
    1. JSON-serializability check  — catches any ORM / date / Decimal that
                                     slipped through context_filter
    2. Null / missing value guards — replaces None with sensible defaults
    3. Stale data detection        — warns if dashboard data is outdated
    4. Numeric sanity checks       — catches division artifacts like inf / nan
    5. Empty context check         — stops the pipeline if no metrics came through
    6. Vague query check           — catches queries too broad to answer usefully
    7. Missing required metrics    — ensures intent-critical keys are present

Usage:
    from C_F01.validator import validate_context
    safe_context = validate_context(filter_result, query)
"""

import json
import math
from datetime import date, datetime
from decimal import Decimal


# ── Sentinels ─────────────────────────────────────────────────────────────────
NUMERIC_FALLBACK     = 0
STRING_FALLBACK      = "N/A"
LIST_FALLBACK        = []
STALE_THRESHOLD_DAYS = 2

# ── Vague query signals ───────────────────────────────────────────────────────
# Queries that match these patterns alone give Claude nothing to work with.
VAGUE_PATTERNS = [
    "tell me everything",
    "show me all",
    "what is the dashboard",
    "give me data",
    "show dashboard",
    "all metrics",
    "everything",
]

# ── Required metrics per intent ───────────────────────────────────────────────
# If these keys are missing from context after filtering, the answer will be
# incomplete. Validator flags it before wasting an API call.
REQUIRED_METRICS = {
    "cashflow": ["total_inflow", "total_outflow", "net_cashflow"],
    "invoice":  ["total_receivable", "open_invoices", "overdue_count"],
    "aging":    ["aging_buckets", "aging_counts", "overdue_amount"],
    "expense":  ["expense_labels", "expense_amounts", "top_expense_category"],
    "client":   ["top_clients", "concentration_pct", "concentration_risk"],
    "source":   ["source_labels", "source_amounts"],
    "summary":  ["latest_balance", "net_cashflow", "total_receivable"],
}


# ── Type coercion ─────────────────────────────────────────────────────────────

def _make_serializable(value):
    """
    Recursively coerces a value into something json.dumps can handle.
    Handles: Decimal, date, datetime, float inf/nan, nested dicts/lists.
    """
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return NUMERIC_FALLBACK
        return value

    if isinstance(value, dict):
        return {k: _make_serializable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_make_serializable(i) for i in value]

    return value


# ── Null guards ───────────────────────────────────────────────────────────────

def _apply_null_guards(context: dict) -> dict:
    """
    Replaces None values with type-appropriate fallbacks.
    Numeric keys get 0, string keys get 'N/A', list keys get [].
    """
    guarded = {}
    for key, value in context.items():
        if value is None:
            # Infer fallback from key name conventions
            if any(x in key for x in ["count", "amount", "pct", "balance",
                                       "inflow", "outflow", "cashflow",
                                       "receivable", "efficiency", "max"]):
                guarded[key] = NUMERIC_FALLBACK
            elif any(x in key for x in ["labels", "buckets", "clients",
                                         "months", "types", "amounts",
                                         "inflows", "outflows", "nets",
                                         "counts", "pcts"]):
                guarded[key] = LIST_FALLBACK
            else:
                guarded[key] = STRING_FALLBACK
        else:
            guarded[key] = value
    return guarded


# ── Stale data detection ──────────────────────────────────────────────────────

def _check_staleness(today) -> dict | None:
    """
    Returns a warning dict if `today` from dashboardCalc is stale,
    else None.
    """
    if today is None:
        return {"warning": "Dashboard date is missing — data freshness unknown."}

    if isinstance(today, str):
        try:
            today = date.fromisoformat(today)
        except ValueError:
            return {"warning": f"Dashboard date format unrecognised: {today}"}

    delta = (date.today() - today).days
    if delta > STALE_THRESHOLD_DAYS:
        return {
            "warning": f"Dashboard data is {delta} day(s) old. "
                       f"Metrics may not reflect today's state."
        }
    return None


# ── JSON serializability check ────────────────────────────────────────────────

def _assert_json_safe(context: dict) -> dict:
    """
    Attempts json.dumps on the full context.
    If it fails, runs _make_serializable as a corrective pass and retries.
    Raises ValueError if it still can't serialize (shouldn't happen after coercion).
    """
    try:
        json.dumps(context)
        return context
    except (TypeError, ValueError):
        coerced = _make_serializable(context)
        try:
            json.dumps(coerced)
            return coerced
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"context_serializer: context is not JSON-safe after coercion. "
                f"Check for custom ORM objects. Error: {e}"
            )


# ── Empty context check ───────────────────────────────────────────────────────

def _check_empty_context(context: dict) -> dict | None:
    """
    Returns an error if the context has no usable metrics.
    An all-zero or all-fallback context is treated as empty.
    """
    if not context:
        return {"error": "No metrics available for this query. Dashboard may not have loaded."}

    non_empty_values = [
        v for v in context.values()
        if v not in (NUMERIC_FALLBACK, STRING_FALLBACK, LIST_FALLBACK, None)
    ]
    if not non_empty_values:
        return {"error": "All metrics returned empty values. Check if transactions exist."}

    return None


# ── Vague query check ─────────────────────────────────────────────────────────

def _check_vague_query(query: str) -> dict | None:
    """
    Returns an error if the query is too broad for a focused answer.
    Prompts the user to ask something more specific.
    """
    if not query or len(query.strip()) < 5:
        return {"error": "Query is too short. Please ask a specific question about your finances."}

    query_lower = query.lower().strip()
    if query_lower in VAGUE_PATTERNS:
        return {
            "error": (
                "Query is too broad. Try something like: "
                "'What are my overdue invoices?' or "
                "'How did cashflow change this month?'"
            )
        }
    return None


# ── Missing required metrics check ───────────────────────────────────────────

def _check_required_metrics(intent: str, context: dict) -> dict | None:
    """
    Checks that intent-critical keys are present and non-empty in context.
    Returns a warning (not error) so Claude can still attempt an answer
    with partial data, but the prompt layer knows to caveat.
    """
    required = REQUIRED_METRICS.get(intent, [])
    missing  = [
        key for key in required
        if key not in context or context[key] in (NUMERIC_FALLBACK, LIST_FALLBACK, STRING_FALLBACK)
    ]
    if missing:
        return {
            "warning": f"Some metrics needed for this answer are missing or zero: {', '.join(missing)}. "
                       f"Answer may be incomplete."
        }
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def validate_context(filter_result: dict, query: str = "") -> dict:
    intent  = filter_result.get("intent", "summary")
    context = filter_result.get("context", {})
    today   = context.pop("today", None)

    # ── Hard stops — don't proceed if these fail ──────────────────────────────
    vague_error = _check_vague_query(query)
    if vague_error:
        return {"intent": intent, "context": {}, "warning": None, **vague_error}

    empty_error = _check_empty_context(context)
    if empty_error:
        return {"intent": intent, "context": {}, "warning": None, **empty_error}

    # ── Sanitize ──────────────────────────────────────────────────────────────
    context = _apply_null_guards(context)
    context = _assert_json_safe(context)

    # ── Soft warnings — proceed but inform the prompt layer ──────────────────
    warnings = []

    stale = _check_staleness(today)
    if stale:
        warnings.append(stale["warning"])

    missing = _check_required_metrics(intent, context)
    if missing:
        warnings.append(missing["warning"])

    return {
        "intent":  intent,
        "context": context,
        "warning": " | ".join(warnings) if warnings else None,
        "error":   None,
    }