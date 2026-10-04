"""
Document Classifier — classifies legal documents reliably using keyword matching
and LLM classification with multi-provider fallback.

Design decisions:
- Keyword-first: fast deterministic check catches 90%+ of legal documents instantly.
- LLM fallback: only for genuinely ambiguous text where keywords don't match.
- Fail-safe = ACCEPT: if all LLM providers fail, document is accepted (not rejected).
  Infrastructure failures must never cause false rejections of genuine legal documents.
- Historic keyword expansion: supports pre-independence and older judgment formats
  (AIR citations, SCR, "their lordships", "delivered the judgment", etc.)
- Threshold: a single strong legal signal is enough to accept (>= 1 match).
"""
import json
import re
from ai_core.llm_gateway import call_llm

REJECTION_MESSAGE = (
    "This document does not appear to be a legal document. NyayaPramaan accepts only law-related documents."
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
    "interlocutory", "special leave", "slp", "revision", "quashing", "gopalan", "madras",
    # ── Historic / Old judgment format keywords (Step 4 expansion) ──
    "air ", "scr", "scj", "all india reporter", "supreme court reports",
    "delivered the judgment", "delivered the judgement", "pronounced the judgment",
    "pronounced the judgement", "hon'ble judges", "hon'ble justice",
    "their lordships", "his lordship", "my lord", "lordship",
    "1950 scr", "1951 scr", "1952 scr", "1953 scr", "1954 scr",
    "privy council", "federal court", "government of india act",
    "dominion of india", "british india", "indian independence",
    "part iii", "part iv", "directive principles", "dpsp",
    "preamble", "sovereign", "socialist", "secular", "democratic republic",
    "original jurisdiction", "appellate jurisdiction", "advisory jurisdiction",
    "writ of", "quo warranto", "res judicata", "stare decisis",
    "ratio decidendi", "obiter dicta", "obiter dictum",
    "locus standi", "amicus curiae", "sub judice", "inter alia",
    "mala fide", "bona fide", "suo motu", "suo moto",
    "first information report", "charge-sheet", "challan",
    "sessions judge", "magistrate", "chief justice",
    "bench of", "division bench", "full bench", "constitutional bench",
    "lok adalat", "nyaya panchayat", "panchayat court",
    "motor accident", "compensation", "consumer forum",
    "national commission", "state commission", "district forum",
    "arbitration", "conciliation", "mediation",
    "writ of habeas corpus", "writ of mandamus", "writ of certiorari",
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


# ── Models to try for classification (uses existing multi-provider chain) ──
_CLASSIFICATION_MODELS = [
    "groq/openai/gpt-oss-20b",
    "gemini/gemini-3.6-flash",
    "openrouter/deepseek/deepseek-r1:free",
]


def classify_document(text_sample: str, filename: str = "") -> dict:
    # 1. Filename-based fast accept
    if filename:
        fn_lower = filename.lower()
        for pat in FILENAME_LEGAL_PATTERNS:
            if re.search(pat, fn_lower):
                return {"is_legal_relevant": True, "document_type": "case_file"}

    # 2. Empty text = accept through (scanned/image docs get full Gemini read later)
    if not text_sample or not text_sample.strip():
        # If extraction is empty (e.g. image-heavy PDF or freshly scanned file), allow through to OCR/Gemini
        return {"is_legal_relevant": True, "document_type": "case_file"}

    lowered = text_sample.lower()
    legal_hits = sum(1 for kw in STRONG_LEGAL_SIGNALS if kw in lowered)
    non_legal_hits = sum(1 for kw in STRONG_NON_LEGAL_SIGNALS if kw in lowered)

    # 3. Any legal signal present makes it legal (threshold = 1, already loose)
    if legal_hits >= 1:
        return {"is_legal_relevant": True, "document_type": "case_file"}

    # 4. Only reject if clear non-legal resume/invoice markers are present and 0 legal signals
    if non_legal_hits >= 2 and legal_hits == 0:
        return {"is_legal_relevant": False, "document_type": "not_legal"}

    # 5. LLM classification with multi-provider retry (Step 3: retry then accept, never reject on error)
    prompt = f"""Classify this document. Respond with ONLY this JSON:
{{"is_legal_relevant": true, "document_type": "case_file"}}

is_legal_relevant is TRUE for: any court case files, judgments, orders, FIRs,
affidavits, legal notices, contracts, statutes, law notes, Indian Kanoon exports, or any legal text.
This includes old/historic judgments from 1950s-60s with different formatting.

is_legal_relevant is FALSE for: resume, job offer letter, shopping invoices, cooking recipes.

DOCUMENT (preview):
{text_sample[:1500]}

JSON:"""

    # Try each model in the fallback chain
    for model in _CLASSIFICATION_MODELS:
        try:
            raw = call_llm(model, prompt)

            # Check for the gateway's "high demand" fallback message — treat as provider failure
            if "experiencing high demand" in raw.lower():
                print(f"[document_classifier] {model} returned rate-limit message, trying next provider")
                continue

            cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
            result = json.loads(cleaned)
            doc_type = result.get("document_type", "case_file")
            is_relevant = bool(result.get("is_legal_relevant", True)) and doc_type != "not_legal"
            return {"is_legal_relevant": is_relevant, "document_type": doc_type}
        except Exception as e:
            print(f"[document_classifier] LLM classification failed with {model}: {e}, trying next provider")
            continue

    # FAIL-SAFE: If ALL providers fail, ACCEPT the document (Step 3 fix).
    # Infrastructure hiccups must never cause false rejections.
    # The document will be processed normally and can be reviewed later.
    print("[document_classifier] All LLM providers failed for classification — accepting document (fail-safe)")
    return {"is_legal_relevant": True, "document_type": "case_file"}
