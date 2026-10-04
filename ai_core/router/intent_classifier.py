"""
Intent Classifier — runs before processing to distinguish legal vs non-legal queries.
"""
import json
import re
from ai_core.llm_gateway import call_llm

CLASSIFIER_MODEL = "groq/openai/gpt-oss-20b"

REFUSAL_MESSAGE = "I can only assist with legal research, legal documents and legal-domain questions."

LEGAL_KEYWORDS = [
    "case", "court", "judge", "judgment", "police", "fir", "bail", "arrest",
    "ipc", "bns", "crpc", "bnss", "cpc", "section", "act", "law", "legal",
    "lawyer", "advocate", "petition", "order", "decree", "affidavit", "notice",
    "contract", "agreement", "fine", "jail", "prison", "punishment", "offence",
    "crime", "theft", "murder", "divorce", "maintenance", "dowry", "property",
    "land", "tenant", "rights", "rights rakshak", "constitution", "article",
    "evidence", "witness", "trial", "appeal", "tribunal", "document", "summary",
    "explain", "accused", "victim", "complainant", "petitioner", "respondent",
    "dhara", "kanoon", "adalat", "mukadma", "faisla", "nyaya", "vakil", "sazaa",
    "overview", "parties", "charge", "allegation", "claim", "clause", "stamp",
    "deed", "registry", "challan", "warrant", "inquiry", "plea", "quash"
]


def classify_intent(query: str) -> dict:
    lowered = query.lower()
    # Fast keyword matching for legal intent
    if any(kw in lowered for kw in LEGAL_KEYWORDS):
        return {"domain": "legal", "audience": "student_public"}

    prompt = f"""Classify this question on two dimensions. Respond with ONLY this JSON:
{{"domain": "legal", "audience": "student_public"}}

domain: "legal" if related to Indian law, legal rights, court procedure, IPC/BNS/CrPC/BNSS statutes,
cases, agreements, contracts, rights, or justice system -- in English, Hindi, or Hinglish.
"out_of_domain" ONLY if completely unrelated to law (e.g., cooking recipes, gaming cheats, sports trivia, coding tutorials, weather).

audience: "professional" or "student_public"

QUESTION: {query}

JSON:"""
    try:
        raw = call_llm(CLASSIFIER_MODEL, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        result = json.loads(cleaned)
        domain = result.get("domain", "legal")
        audience = result.get("audience", "student_public")
        if domain not in ("legal", "out_of_domain"):
            domain = "legal"
        if audience not in ("professional", "student_public"):
            audience = "student_public"
        return {"domain": domain, "audience": audience}
    except Exception:
        return {"domain": "legal", "audience": "student_public"}


AUDIENCE_INSTRUCTIONS = {
    "professional": (
        "PROFESSIONAL LEGAL MODE: Provide in-depth legal research with exact statutory sections, judicial doctrines (ratio decidendi, obiter dictum), precedents, procedural remedies, and evidentiary requirements. Be rigorous, structured, and precise."
    ),
    "student": (
        "STUDENT ACADEMIC MODE: Focus on clear conceptual explanations, breakdown of legal elements (mens rea, actus reus, ingredient tests), landmark case law precedents, and comparative statutory analysis (e.g., IPC vs BNS)."
    ),
    "citizen": (
        "CITIZEN PLAIN-LANGUAGE MODE: Explain the legal issue in clear, empathetic, non-jargon language. Outline the user's practical rights, step-by-step procedure (e.g., filing an FIR/complaint, sending a legal notice), and relevant authorities. Include an informational disclaimer."
    ),
    "student_public": (
        "Write in a clear, accessible, and structured manner: explain key legal terms, cite relevant statutes/sections, and provide actionable context."
    ),
}


