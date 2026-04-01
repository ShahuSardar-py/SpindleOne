
from .context_filter import filter_context_for_query
from .validator      import validate_context
from .prompts        import build_prompt
from .LLM            import call_llm


# ── Public API ────────────────────────────────────────────────────────────────

def chat(query: str) -> dict:
    # ── Step 1: Filter ────────────────────────────────────────────────────────
    # Calls dashboardCalc, detects intent, returns relevant metric subset
    filter_result = filter_context_for_query(query)

    # ── Step 2: Validate ──────────────────────────────────────────────────────
    # Sanitizes types, checks for empty/vague/missing metrics
    validated = validate_context(filter_result, query)

    # Hard stop — don't waste an API call if context is unusable
    if validated.get("error"):
        return {
            "answer":  None,
            "intent":  validated.get("intent"),
            "warning": None,
            "error":   validated["error"],
        }

    # ── Step 3: Build Prompt ──────────────────────────────────────────────────
    prompt = build_prompt(validated=validated, query=query)

    # ── Step 4: Call LLM ──────────────────────────────────────────────────────
    answer = call_llm(prompt)

    return {
        "answer":  answer,
        "intent":  validated["intent"],
        "warning": validated.get("warning"),
        "error":   None,
    }