"""ai_core/rag/legal_scope.py (NEW) - domain gate, topic->sections map, fixed follow-up suggestions. No LLM calls.
Domain: Police, FIR aur Bail (BNS/BNSS/BSA)."""
import re

TOPICS = [
    (r"\bfir\b|\bf\.i\.r|zero fir|complaint (nahi|not) (likh|regist)|likhne se mana|report (nahi|not) (likh|lag)|shikayat",
     [("BNSS", "173"), ("BNSS", "175")], "fir"),
    (r"anticipatory|agrim zamanat|arrest hone se pehle|giraftari se pehle", [("BNSS", "482")], "bail"),
    (r"default bail|60 din|90 din|chargesheet (nahi|not)|remand|24 (ghante|hours)", [("BNSS", "187"), ("BNSS", "58")], "bail"),
    (r"undertrial|jail me .*(saal|year)|aadhi saza|half.*sentence", [("BNSS", "479")], "bail"),
    (r"\bbail\b|zamanat|jamanat|bailable|non.?bailable", [("BNSS", "478"), ("BNSS", "480"), ("BNSS", "482")], "bail"),
    (r"\barrest|giraft|pakad|warrant|police (utha|le gayi|pakad)", [("BNSS", "35"), ("BNSS", "47"), ("BNSS", "58")], "arrest"),
    (r"\btheft\b|chori", [("BNS", "303")], "offence"),
    (r"cheating|dhokha|fraud|thagi|420", [("BNS", "318")], "offence"),
    (r"498a|dowry|dahej|sasural.*(maar|cruelty)|cruelty", [("BNS", "85"), ("BNS", "86")], "offence"),
    (r"molest|chhed|eve.?teas|modesty", [("BNS", "74"), ("BNS", "79")], "offence"),
]
SUGGEST = {
    "fir": ["Agar police FIR likhne se mana kare to kya karein?", "Zero FIR kya hoti hai?", "FIR ke baad aage kya hota hai?"],
    "bail": ["Anticipatory bail kab mil sakti hai?", "Default bail kab milti hai?", "Bailable aur non-bailable me kya fark hai?"],
    "arrest": ["Giraftari par mere kya adhikar hain?", "Police kitne ghante me court me pesh karegi?", "Giraftari ke baad zamanat kaise milti hai?"],
    "offence": ["Is par FIR kaise darj karein?", "Is offence me zamanat milti hai kya?", "IPC ka kaunsa section ab BNS me kis number par hai?"],
    "default": ["FIR kaise darj karein?", "Zamanat (bail) kaise milti hai?", "IPC 302 ab BNS me kaunsa section hai?"],
}
_IN = re.compile(r"\b(fir|police|thana|bail|zamanat|jamanat|arrest|giraft|remand|chargesheet|bns|bnss|bsa|ipc|crpc|section|dhara|"
                 r"cheque|check bounce|ni act|138|theft|chori|murder|hatya|fraud|cheating|dowry|dahej|court|magistrate|saza|"
                 r"punishment|offence|crime|complaint|shikayat|vakil|lawyer|evidence|sakshya|legal aid|nalsa|dlsa|cyber|upi)\b", re.I)
_OUT = re.compile(r"\b(zameen|jameen|land|property|plot|registry|mutation|divorce|talaq|custody|maintenance|alimony|will|vasiyat|"
                  r"inheritance|tax|gst|itr|labour|salary|pf|consumer|rti|tenant|kiraya|landlord|trademark|patent)\b", re.I)
OUT_MSG = ("Abhi hamara platform sirf **Police, FIR aur Bail** (BNS/BNSS/BSA, IPC/CrPC mapping) par verified jawab deta hai. "
           "Is sawal ke liye apne vakil ya DLSA (free legal aid, NALSA 15100) se sampark karein.")


def topic_key(query: str):
    for rx, _, key in TOPICS:
        if re.search(rx, query or "", re.I):
            return key
    return None


def topic_sections(query: str) -> list[tuple[str, str]]:
    """Sections of the FIRST matching topic only (keeps evidence focused)."""
    for rx, secs, _ in TOPICS:
        if re.search(rx, query or "", re.I):
            return secs
    return []


def in_scope(query: str) -> bool:
    """False only for clearly out-of-domain questions (land, divorce, tax...) that have no police/criminal keyword."""
    q = query or ""
    return bool(_IN.search(q)) or not _OUT.search(q)


def suggestions_for(query: str) -> list[str]:
    return SUGGEST.get(topic_key(query) or "default")