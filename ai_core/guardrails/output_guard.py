
"""Output Guardrails — redacts PII from final responses."""

import re



PII_PATTERNS = {

    "aadhaar": r"\b\d{4}\s\d{4}\s\d{4}\b|\b\d{4}-\d{4}-\d{4}\b",

    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",

    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",

    "phone": r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b|\b\d{10}\b",

}





def redact_pii(text: str) -> str:

    for label, pattern in PII_PATTERNS.items():

        text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)

    return text

