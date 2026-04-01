"""
chat.py
-------
Orchestrator for the metric store architecture.

Flow:
    1. Load metric store (cached, TTL-based)
    2. Build prompt with store + user query
    3. Call LLM
    4. Return answer

No intent detection. No context filtering. No routing.
The LLM reads the store and decides what's relevant.
"""

from .metric_Store import get_metric_store
from .prompts      import build_prompt
from .LLM          import call_llm


def chat(query: str) -> dict:
    """
    Main entry point for the chat feature.

    Args:
        query: Raw user message from the frontend.

    Returns:
        {
            "answer" : str,        — LLM response
            "error"  : str | None  — only set on hard failure
        }
    """

    if not query or not query.strip():
        return {
            "answer": None,
            "error":  "Query cannot be empty."
        }

    # ── Step 1: Load metric store ─────────────────────────────────────────────
    # Returns cached JSON if within TTL, rebuilds if stale
    metric_store = get_metric_store()

    # ── Step 2: Build prompt ──────────────────────────────────────────────────
    prompt = build_prompt(query=query, metric_store=metric_store)

    # ── Step 3: Call LLM ──────────────────────────────────────────────────────
    answer = call_llm(prompt)

    # LLM.py returns "[LLM ERROR] ..." string on failure
    if answer.startswith("[LLM ERROR]"):
        return {
            "answer": None,
            "error":  answer
        }

    return {
        "answer": answer,
        "error":  None
    }