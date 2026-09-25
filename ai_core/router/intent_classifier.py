"""
Intent Classifier — runs before processing to distinguish legal vs non-legal queries.
"""
import json
import re
from ai_core.llm_gateway import call_llm

CLASSIFIER_MODEL = "groq/openai/gpt-oss-20b"

REFUSAL_MESSAGE = (
    "I specialize exclusively in Indian law, legal rights, court procedures, and case documents. "
    "Please ask a legal or case-related question."
)

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
"out_of_domain" ONLY if completely unrelated to law (e.g., cooking recipes, gaming cheats, sports trivia, coding tutorials).

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
        "Write for a legal professional: use precise legal terminology, "
        "cite exact section numbers, and include procedural nuance. Directly answer without filler or repetitive AI intros."
    ),
    "student_public": (
        "Write for a student or citizen: use simple, plain language, "
        "briefly define any legal term you must use, and keep a clear, helpful tone. Directly answer without repetitive robotic disclaimers."
    ),
}

