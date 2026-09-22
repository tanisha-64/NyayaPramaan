"""
Output Guardrails (synopsis Section 4.2)
Screens outgoing responses for PII before they reach the user.
"""
import re

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b|\b\d{10}\b",
    "aadhaar": r"\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b",
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
}

def redact_pii(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)
    return text