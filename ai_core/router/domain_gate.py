"""
domain_gate.py  (NEW FILE)  ->  ai_core/router/domain_gate.py

Law-only gate. Runs BEFORE retrieval, web search, verification or any "Evidence status".

check_domain(query, has_document, ask_llm) -> one of
    "legal"      : law question / legal scenario / question about the attached document
    "greeting"   : hi, hello, thanks ... (friendly canned reply, no LLM, no sources)
    "injection"  : tries to change the assistant's role / reveal instructions / bypass rules
    "off_topic"  : not about law (e.g. "What is love?")

Order: injection -> greeting -> obvious legal words (no LLM) -> one cheap YES/NO LLM check.
If the LLM is unavailable for an ambiguous message we REFUSE (safe default).
"""
import re
from functools import lru_cache

from ai_core.router.intent_rules import prefilter_label

_INJECTION = re.compile(
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|rules)"
    r"|disregard (the |all )?(system|previous|above)"
    r"|(reveal|show|print|repeat|leak) (me )?(your |the )?(system|hidden|initial) (prompt|instructions?)"
    r"|\bsystem prompt\b|\bdeveloper mode\b|\bjailbreak\b|\bdan mode\b"
    r"|you are now\b|\bpretend (to be|you are)\b|\bact as (if|a|an|my)\b|\broleplay as\b"
    r"|forget (your|all) (rules|instructions)|bypass (your |the )?(rules|safety|filters?)"
    r"|(api|secret|service)[ _-]?key|\.env\b|service[_ ]role",
    re.I,
)

_GREETING = re.compile(
    r"^\s*(hi+|hello+|hey+|hii+|namaste|namaskar|good\s+(morning|afternoon|evening|night)|"
    r"thanks?( you)?|thank you( so much)?|dhanyawad|shukriya|ok(ay)?|bye|goodbye)\W*$",
    re.I,
)

_LEGAL = re.compile(
    r"\b(law|laws|legal|illegal|lawful|unlawful|lawyer|advocate|attorney|court|courts|judge|judgment|judgement|"
    r"verdict|tribunal|case|cases|act|acts|section|sections|article|clause|bns|bnss|bsa|ipc|crpc|cpc|constitution|"
    r"constitutional|statute|ordinance|bye-?law|fir|police|arrest|arrested|bail|custody|remand|warrant|summons|"
    r"challan|notice|petition|appeal|suit|plaintiff|defendant|accused|victim|complainant|witness|evidence|"
    r"affidavit|crime|criminal|offen[cs]e|theft|robbery|murder|fraud|cheating|forgery|cheque|bounce|defamation|"
    r"harassment|stalking|dowry|domestic violence|divorce|alimony|maintenance|marriage|custody|adoption|will|"
    r"inheritance|succession|property|land|plot|tenant|tenancy|landlord|rent|eviction|lease|mortgage|registry|"
    r"mutation|possession|encroachment|trespass|contract|agreement|breach|consumer|refund|warranty|complaint|rti|"
    r"rights?|fundamental|tax|gst|itr|employer|employee|salary|wages|termination|gratuity|posh|cyber|hacking|scam|"
    r"privacy|copyright|trademark|patent|fine|penalty|punishment|imprisonment|jail|sentence|jurisdiction|"
    r"limitation|injunction|decree|hearing|licen[cs]e|accident|insurance|compensation|damages|legal aid|helpline|"
    r"kanoon|kanun|adalat|vakil|dhara|saza|sazaa|jurm|thana|muqadma|zamin|jameen|kiraya|kirayedar|talaq|dahej|"
    r"sanvidhan|nyay|nyaya|jamanat)\b"
    r"|कानून|अदालत|वकील|धारा|केस|पुलिस|सज़ा|सजा|जमानत|तलाक|मुकदमा|न्याय|संविधान|अधिकार|किरायेदार|ज़मीन|जमीन",
    re.I,
)

GREETING_REPLY_EN = ("Hello! 👋 I'm NyayaPramaan. Ask me any legal question, describe a situation you're facing, "
                     "or upload a legal document, and I'll help with answers backed by sources.")
GREETING_REPLY_HI = ("Namaste! 👋 Main NyayaPramaan hu. Aap koi bhi kanooni sawal poochh sakte hain, apni situation bata "
                     "sakte hain ya legal document upload kar sakte hain. Main sources ke saath jawab dunga.")

_YESNO_PROMPT = """Answer with exactly one word: YES or NO.
Is the following message a question or request about law, legal rights, legal procedure, a legal document, \
or a real-life situation with legal implications (police, property, contracts, workplace, family, consumer, tax, crime)?
Greetings, general knowledge, entertainment, coding, math, relationships/philosophy and small talk are NO.

MESSAGE: {q}

ANSWER:"""


def check_domain(query: str, has_document: bool, ask_llm=None) -> str:
    q = (query or "").strip()
    if not q:
        return "off_topic"
    if _INJECTION.search(q):
        return "injection"
    if _GREETING.match(q):
        return "greeting"
    if _LEGAL.search(q) or prefilter_label(q, has_document) in ("CASE_SPECIFIC", "MIXED"):
        return "legal"
    if ask_llm is None:
        return "off_topic"
    return "legal" if _cached_llm_yes(q, ask_llm) else "off_topic"


_CACHE: dict[str, bool] = {}


def _cached_llm_yes(q: str, ask_llm) -> bool:
    key = q.lower()[:300]
    if key in _CACHE:
        return _CACHE[key]
    try:
        raw = ask_llm(_YESNO_PROMPT.format(q=q[:500])) or ""
        ans = raw.strip().upper().startswith("YES")
        if raw.strip():                       # do not cache failures
            if len(_CACHE) > 500:
                _CACHE.clear()
            _CACHE[key] = ans
        return ans
    except Exception:
        return False                          # unavailable -> refuse (safe default)


def greeting_reply(hinglish: bool) -> str:
    return GREETING_REPLY_HI if hinglish else GREETING_REPLY_EN


_DOC_MARK = re.compile(r"\b(petitioner|respondent|appellant|plaintiff|defendant|whereas|hereby|witnesseth|versus|hon'?ble|"
                       r"decree|prayer|be it enacted|short title|affidavit|sub-?section|complainant|lessor|lessee)\b", re.I)
_DOC_PROMPT = """Answer with exactly one word: YES or NO.
Is this document ITSELF a legal document: court judgment/order, petition, FIR, notice, contract/agreement, statute/rules, \
legal opinion, or a law assignment/case study? Project reports, proposals, budgets, resumes, invoices and articles \
are NO even if they mention law.

DOCUMENT START:
{t}

ANSWER:"""


def is_legal_document(text: str, ask_llm) -> bool:
    """Upload gate: strong legal markers pass without an LLM; otherwise one strict YES/NO call."""
    t = (text or "").strip()
    if len({m.lower() for m in _DOC_MARK.findall(t[:20000])}) >= 3:
        return True
    try:
        return (ask_llm(_DOC_PROMPT.format(t=t[:3000])) or "").strip().upper().startswith("YES")
    except Exception:
        return False