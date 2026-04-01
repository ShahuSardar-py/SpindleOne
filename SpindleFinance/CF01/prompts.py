
# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a senior financial analyst assistant named C-F01, specializing in actionalble analysis of finance data. 

Rules:
- ONLY use the provided context.
- DO NOT hallucinate or assume missing data.
- If data is insufficient, explicitly say "Insufficient data".
- Be concise but insightful.
- Focus on explaining trends, causes, and implications.
- Prefer clarity over verbosity.
"""


# ── Intent-specific instructions ──────────────────────────────────────────────

INTENT_INSTRUCTIONS = {
    "cashflow": """
Analyze cash inflow, outflow, and net cashflow.
Explain trends, imbalances, and possible reasons. Be consise and provide actionalble points. 
""",

    "invoice": """
Analyze receivables, open invoices, and overdue counts.
Highlight risks in collections and delays.
""",

    "aging": """
Analyze aging buckets and overdue amounts.
Identify risk concentration in older buckets.
""",

    "expense": """
Analyze expense distribution and top categories.
Highlight cost drivers and anomalies.
""",

    "client": """
Analyze client concentration and dependency risks.
Identify if revenue is overly dependent on few clients.
""",

    "source": """
Analyze income sources and their contribution.
Highlight diversification vs concentration.
""",

    "summary": """
Provide a concise financial overview.
Cover balance, cashflow, and receivables.
Highlight key risks and signals.
"""
}


# ── Context Formatting 

def _format_context(context: dict) -> str:
    """
    Converts context dict into LLM-friendly structured text.
    """
    lines = []
    for key, value in context.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


# ── Warning Injection 

def _format_warning(warning: str | None) -> str:
    if not warning:
        return ""

    return f"""
Important Notes:
{warning}

If these affect the answer, explicitly mention limitations.
"""


# ── Final Prompt Builder 

def build_prompt(validated: dict, query: str) -> str:

    intent = validated.get("intent", "summary")
    context = validated.get("context", {})
    warning = validated.get("warning")

    intent_instruction = INTENT_INSTRUCTIONS.get(
        intent, INTENT_INSTRUCTIONS["summary"]
    )
    context_block = _format_context(context)
    warning_block = _format_warning(warning)

    prompt = f"""
{SYSTEM_PROMPT}

Task:
{intent_instruction}

Context:
{context_block}

{warning_block}

User Question:
{query}

Answer:
"""

    return prompt.strip()