
"""

Document Classifier — classifies the FULL extracted text (passed in by

the caller), with a deterministic fast-path for obvious cases/judgments

(including older/historic formats) and an LLM fallback only for genuinely

ambiguous documents. On any LLM failure, defaults to ACCEPT (a false

reject of a real case file is worse than rarely accepting an edge-case --

TrustAgent/verification layers downstream still apply strict accuracy

checks regardless).

"""

import json

import re

from ai_core.llm_gateway import call_llm



REJECTION_MESSAGE = (

    "This document does not appear to be a legal case document or "

    "law-related study material. NyayaPramaan only analyzes case files, "

    "judgments, FIRs, affidavits, legal notices, contracts under dispute, "

    "statutes, or law-student materials. Please upload a relevant document."

)



STRONG_LEGAL_SIGNALS = [

    "plaintiff", "defendant", "petitioner", "respondent", "appellant",

    "hon'ble court", "hon'ble supreme court", "in the court of", "suit no",

    "case no", "fir no", "affidavit", "learned counsel", "judgment",

    "order dated", "partition", "decree", "cause of action", "jurisdiction",

    "constitution of india", "writ petition", "article 21", "article 19",

    "article 14", "bench", "judgment reserved", "reported in", "air 19",

    "scc", "manu/sc", "sessions court", "district court", "high court",

    "criminal appeal", "civil appeal", "special leave petition",

    "preventive detention", "habeas corpus", "hon'ble judges",

    "delivered the judgment", "scr",

]



STRONG_NON_LEGAL_SIGNALS = [

    "dear candidate", "internship offer", "we are pleased to offer",

    "curriculum vitae", "date of birth :", "invoice no", "purchase order",

]





def classify_document(text_sample: str) -> dict:

    lowered = text_sample.lower()

    legal_hits = sum(1 for kw in STRONG_LEGAL_SIGNALS if kw in lowered)

    non_legal_hits = sum(1 for kw in STRONG_NON_LEGAL_SIGNALS if kw in lowered)



    # Loosened fast-path: 1+ strong legal signal (and no non-legal signals) is enough.

    if legal_hits >= 1 and non_legal_hits == 0:

        return {"is_legal_relevant": True, "document_type": "case_file"}



    if non_legal_hits >= 1 and legal_hits == 0:

        return {"is_legal_relevant": False, "document_type": "not_legal"}



    # Ambiguous -- fall back to LLM

    prompt = f"""Classify this document strictly. Respond with ONLY this JSON:

{{"is_legal_relevant": true, "document_type": "case_file"}}



is_legal_relevant is TRUE for: court case files, judgments, orders, FIRs,

affidavits, legal notices, contracts under dispute, statutes, or

law-student study material -- INCLUDING old/historic Supreme Court and

High Court judgments, even if OCR-quality or formatting is imperfect.



is_legal_relevant is FALSE for: offer letters, resumes, personal letters,

business documents, or anything unrelated to an actual legal matter.



document_type: one of "case_file", "judgment", "fir", "affidavit",

"legal_notice", "contract_in_dispute", "statute", "student_material", "not_legal"



DOCUMENT (first portion):

{text_sample}



JSON:"""

    try:

        raw = call_llm("groq/openai/gpt-oss-20b", prompt)

        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

        result = json.loads(cleaned)

        doc_type = result.get("document_type", "other_legal")

        is_relevant = bool(result.get("is_legal_relevant", True)) and doc_type != "not_legal"

        return {"is_legal_relevant": is_relevant, "document_type": doc_type}

    except Exception:

        # Fail-SAFE toward ACCEPTING (a false-reject of a genuine case file

        # is the worse failure mode -- infrastructure hiccups should not

        # block legitimate legal documents).

        return {"is_legal_relevant": True, "document_type": "other_legal"}

