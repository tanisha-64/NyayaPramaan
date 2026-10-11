"""
PII redaction for structured Indian personal identifiers (Aadhaar, PAN, e-mail, phone).

Used at processing boundaries where the identifier is not needed to do the job:
  * text sent to external LLM / embedding / web-search providers (queries, evidence blocks, summary input)
  * final answers and evidence excerpts shown to the user
  * the audit log (query_log)
It is deliberately NOT applied to the stored original document, to retrieval indexes, or to page numbers, so evidence
and citations stay intact. Only structured identifiers are touched: names, dates and addresses are legal facts and are
never blanked out here. Bare long numbers are NOT treated as phone numbers (case numbers, CNR numbers, amounts and
account numbers must survive); a number is redacted only if it has the Indian mobile format or sits next to a
phone / Aadhaar context word.
"""

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
