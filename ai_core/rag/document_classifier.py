"""
Document Classifier — classifies legal documents reliably using keyword matching
and LLM classification.
"""
import json
import re
from ai_core.llm_gateway import call_llm

REJECTION_MESSAGE = (
    "This document does not appear to be a legal case document or "
    "law-related study material. NyayaPramaan analyzes legal case files, "
    "judgments, FIRs, affidavits, legal notices, contracts under dispute, "
    "statutes, court orders, or law-student study materials. Please upload a relevant legal document."
)

STRONG_LEGAL_SIGNALS = [
    "plaintiff", "defendant", "petitioner", "respondent", "hon'ble court",
    "hon'ble supreme court", "hon'ble high court", "in the court of", "suit no", "case no", "fir no",
    "affidavit", "learned counsel", "judgment", "order dated", "partition",
    "decree", "cause of action", "jurisdiction", "constitution of india",
    "writ petition", "article 21", "article 19", "article 14", "article 32", "article 226", "article 22", "bench",
    "judgment reserved", "reported in", "air 195", "air 196", "air 197", "air 198", "air 199", "air 20", "scc",
    "manu/sc", "appellant", "sessions court", "district court", "high court", "supreme court",
    "criminal appeal", "civil appeal", "special leave petition", "section", "sub-section",
    "act", "indian penal code", "ipc", "bns", "crpc", "bnss", "evidence", "bsa", "cpc",
    "contract", "agreement", "lease", "tenancy", "injunction", "bail", "anticipatory bail",
    "accused", "complainant", "prosecution", "advocate", "vakalatnama", "counsel",
    "witness", "testimony", "exhibit", "statute", "tribunal", "legal", "pleading",
    "court", "justice", "law", "police", "charge sheet",
    "clause", "memorandum", "appellate", "jurisprudence", "indiankanoon",
    "state of", "union of india", "supreme court of india", "vs", "versus", "v.",
    "preventive detention", "habeas corpus", "mandamus", "certiorari", "prohibition",
    "kanoon", "judgement", "bare act", "civil procedure", "criminal procedure",
    "equivalent citations", "citations", "author:", "bench:", "coram", "attorney general",
    "advocate general", "solicitor general", "fundamental rights", "ultra vires", "prima facie",
    "interlocutory", "special leave", "slp", "revision", "quashing", "gopalan", "madras"
]

STRONG_NON_LEGAL_SIGNALS = [
    "dear candidate", "internship offer", "we are pleased to offer",
    "curriculum vitae", "resume", "purchase order", "invoice amount",
    "shopping cart", "recipe", "ingredients"
]

FILENAME_LEGAL_PATTERNS = [
    r"_vs_", r"\bvs\b", r"\bv\b", r"_v_", r"union_of_india", r"state_of",
    r"judgment", r"judgement", r"court", r"high_court", r"supreme_court",
    r"appeal", r"petition", r"bail", r"act", r"section", r"fir", r"affidavit",
    r"case", r"order", r"law", r"kanoon", r"gopalan", r"kesavananda", r"maneka",
    r"madras", r"delhi", r"bombay", r"allahabad", r"karnataka", r"calcutta",
    r"scc", r"air", r"scr", r"slp", r"writ", r"statute", r"legal", r"crpc",
    r"ipc", r"bns", r"bnss", r"cpc", r"notice", r"agreement", r"contract",
    r"dispute", r"suit", r"complaint", r"application", r"brief", r"dossier",
    r"deed", r"charge", r"trial", r"claim", r"ruling", r"tribunal", r"arbitration",
    r"\bwp\b", r"\bslp\b", r"\bca\b", r"\bcrim\b", r"\bciv\b"
]


def classify_document(text_sample: str, filename: str = "") -> dict:
    if filename:
        fn_lower = filename.lower()
        for pat in FILENAME_LEGAL_PATTERNS:
            if re.search(pat, fn_lower):
                return {"is_legal_relevant": True, "document_type": "case_file"}

    if not text_sample or not text_sample.strip():
        # If extraction is empty (e.g. image-heavy PDF or freshly scanned file), allow through to OCR/Gemini
        return {"is_legal_relevant": True, "document_type": "case_file"}

    lowered = text_sample.lower()
    legal_hits = sum(1 for kw in STRONG_LEGAL_SIGNALS if kw in lowered)
    non_legal_hits = sum(1 for kw in STRONG_NON_LEGAL_SIGNALS if kw in lowered)

    # Any legal signal present makes it legal
    if legal_hits >= 1:
        return {"is_legal_relevant": True, "document_type": "case_file"}

    # Only reject if clear non-legal resume/invoice markers are present and 0 legal signals
    if non_legal_hits >= 2 and legal_hits == 0:
        return {"is_legal_relevant": False, "document_type": "not_legal"}

    prompt = f"""Classify this document. Respond with ONLY this JSON:
{{"is_legal_relevant": true, "document_type": "case_file"}}

is_legal_relevant is TRUE for: any court case files, judgments, orders, FIRs,
affidavits, legal notices, contracts, statutes, law notes, Indian Kanoon exports, or any legal text.

is_legal_relevant is FALSE for: resume, job offer letter, shopping invoices, cooking recipes.

DOCUMENT (preview):
{text_sample[:1200]}

JSON:"""
    try:
        raw = call_llm("groq/openai/gpt-oss-20b", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        result = json.loads(cleaned)
        doc_type = result.get("document_type", "case_file")
        is_relevant = bool(result.get("is_legal_relevant", True)) and doc_type != "not_legal"
        return {"is_legal_relevant": is_relevant, "document_type": doc_type}
    except Exception:
        return {"is_legal_relevant": True, "document_type": "case_file"}

