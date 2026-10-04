
"""Output Guardrails — redacts PII from final responses."""

import re



PII_PATTERNS = {

    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",

    "phone": r"\b\d{10}\b",

}





def redact_pii(text: str) -> str:

    for label, pattern in PII_PATTERNS.items():

        text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)

    return text

