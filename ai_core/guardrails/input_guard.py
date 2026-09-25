"""
Input Guardrails (Section 4.2) -- pure-Python, zero external network dependency.
Blocks jailbreak, prompt-injection, and instruction-override attempts before reaching LLM,
while allowing genuine legal questions, court orders, and case inquiries.
"""
import re

# Precise injection & jailbreak regex patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|rules|commands|guidelines)",
    r"disregard\s+(all\s+)?(previous|prior|system)\s+(instructions|rules|directives)",
    r"forget\s+(all\s+)?(previous|prior)\s+(instructions|rules|context)",
    r"system\s+(override|prompt\s+leak|instruction\s+leak)",
    r"(reveal|print|show|output|leak)\s+(your\s+)?(system\s+prompt|initial\s+instructions|secret\s+prompt)",
    r"(you\s+are\s+now|act\s+as)\s+(an?\s+)?(unrestricted|jailbroken|dan|evil|rogue|unfiltered)\s+(ai|assistant|model|agent)",
    r"developer\s+mode\s+(enabled|activated|on)",
    r"bypass\s+(all\s+)?(content|safety|guardrail|ethical)\s+(filters|checks|rules)",
    r"do\s+anything\s+now\s+(mode)?",
    r"simulate\s+(jailbreak|dan\s+mode|root\s+access)",
]

COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

def check_input_safety(query: str) -> dict:
    """
    Validates input safety.
    Returns: {"is_safe": bool, "reason": str | None}
    """
    if not query or not query.strip():
        return {"is_safe": True, "reason": None}

    cleaned = " ".join(query.split())

    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            return {
                "is_safe": False,
                "reason": "Prompt manipulation or system instruction override attempt detected.",
            }

    return {"is_safe": True, "reason": None}