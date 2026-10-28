"""ai_core/rag/legal_scope.py - domain gate, topic->sections map, fixed answers, suggestions.
Domain: Police, FIR aur Bail (BNS/BNSS/BSA + IPC/CrPC/NI Act mapping).
No LLM calls."""
import re

# ── topic regex -> (sections to fetch as evidence, suggestion key) ──────
TOPICS = [
    # ── FIR & complaint ──
    (r"\bfir\b|\bf\.i\.r|zero fir|complaint (nahi|not) (likh|regist)|likhne se mana|report (nahi|not) (likh|lag)|shikayat darj",
     [("BNSS", "173"), ("BNSS", "175")], "fir"),
    (r"fir (nahi likh|darj nahi|refuse|mana)|police.*(nahi sun|nahi lik|refuse|mana)|complaint (reject|refuse)",
     [("BNSS", "173"), ("BNSS", "175")], "fir_refuse"),

    # ── Bail ──
    (r"anticipatory|agrim zamanat|arrest hone se pehle|giraftari se pehle",
     [("BNSS", "482")], "anticipatory_bail"),
    (r"default bail|statutory bail|60 din|90 din|chargesheet (nahi|not)|remand|hirasat",
     [("BNSS", "187"), ("BNSS", "58")], "default_bail"),
    (r"undertrial|jail me .*(saal|year)|aadhi saza|half.*sentence|vichar.?adheen",
     [("BNSS", "479")], "undertrial"),
    (r"\bbail\b|zamanat|jamanat|bailable|non.?bailable",
     [("BNSS", "478"), ("BNSS", "480"), ("BNSS", "482")], "bail"),

    # ── Arrest & rights ──
    (r"\barrest|giraft|pakad|warrant|police (utha|le gayi|pakad)|hathkadi|handcuff",
     [("BNSS", "35"), ("BNSS", "47"), ("BNSS", "58")], "arrest"),
    (r"24 (ghante|hours|hrs)|magistrate.*(pesh|produce)|police custody",
     [("BNSS", "58"), ("BNSS", "187")], "arrest"),

    # ── Cheque bounce (NI Act) ──
    (r"cheque|check bounce|bounce|dishonou?r|\b138\b|ni act",
     [("NI", "138"), ("NI", "139"), ("NI", "142"), ("NI", "143A")], "cheque"),

    # ── Murder & culpable homicide ──
    (r"murder|hatya|qatl|maar dala|jaan se maar|\b302\b|\b304\b",
     [("BNS", "101"), ("BNS", "103"), ("BNS", "105")], "murder"),

    # ── Robbery, dacoity, extortion ──
    (r"robbery|loot|dacoity|dakait|\b392\b|\b395\b",
     [("BNS", "309"), ("BNS", "310")], "robbery"),
    (r"extortion|vasool|hafta|dhamki.*(paisa|rupa)",
     [("BNS", "308")], "extortion"),

    # ── Kidnapping ──
    (r"kidnap|aghwa|abduct|utha le gaya|bhagaya|\b363\b|\b364\b",
     [("BNS", "137"), ("BNS", "140")], "kidnapping"),

    # ── Sexual offences ──
    (r"\brape\b|balatkar|sexual assault|jabardasti.*sambandh|\b376\b",
     [("BNS", "63"), ("BNS", "64"), ("BNS", "65")], "sexual_offence"),
    (r"molest|chhed|eve.?teas|modesty|outrag|sexual harass|vishaka",
     [("BNS", "74"), ("BNS", "79")], "molestation"),
    (r"stalking|peechha|track kar",
     [("BNS", "78")], "stalking"),
    (r"voyeurism|taka?-jhank|secretly.*record|privacy.*record",
     [("BNS", "77")], "voyeurism"),

    # ── Dowry / domestic ──
    (r"498a|dowry|dahej|sasural.*(maar|cruelty)|cruelty.*wife|domestic violence|gharelu hinsa",
     [("BNS", "85"), ("BNS", "86")], "dowry"),

    # ── Theft ──
    (r"\btheft\b|chori|\b379\b|\b380\b",
     [("BNS", "303"), ("BNS", "305")], "theft"),

    # ── Cheating & fraud ──
    (r"cheating|dhokha|fraud|thagi|\b420\b|cyber.*fraud|online.*fraud|upi.*fraud",
     [("BNS", "318"), ("BNS", "319")], "fraud"),

    # ── Assault / hurt ──
    (r"assault|marpeet|maar.?peet|hurt|chot|grievous|ghambhir chot|\b323\b|\b325\b",
     [("BNS", "115"), ("BNS", "117"), ("BNS", "118")], "assault"),

    # ── Criminal intimidation / threatening ──
    (r"intimidat|dhamki|threat|dharamki|jaan se maarne ki dhamki|\b506\b",
     [("BNS", "351")], "intimidation"),

    # ── Trespass ──
    (r"trespass|ghuspaith|ghar me ghus|home invasion|\b441\b|\b448\b",
     [("BNS", "329"), ("BNS", "331")], "trespass"),

    # ── Defamation ──
    (r"defam|maanhaani|badnaami|izzat.*kharab|\b499\b|\b500\b",
     [("BNS", "356")], "defamation"),

    # ── Drunk driving / rash driving ──
    (r"drunk driv|nashe me gaadi|rash driv|tez gaadi|road accident|accident.*death|\b304a\b|\b279\b",
     [("BNS", "281"), ("BNS", "106")], "driving"),

    # ── Rioting ──
    (r"riot|danga|mob|bheed.*hinsa|stone.*pelt|\b147\b|\b148\b",
     [("BNS", "189"), ("BNS", "191")], "rioting"),

    # ── Forgery / counterfeiting ──
    (r"forg|jaalsaazi|nakli dastavez|fake document|\b463\b|\b465\b",
     [("BNS", "336"), ("BNS", "338")], "forgery"),

    # ── Criminal conspiracy ──
    (r"conspirac|saazish|milkar plan|\b120b\b",
     [("BNS", "61")], "conspiracy"),

    # ── Attempt to murder ──
    (r"attempt.*(murder|kill)|jaan.*koshish|maar.*koshish|\b307\b",
     [("BNS", "109")], "attempt_murder"),

    # ── Acid attack ──
    (r"acid|tezaab|\b326a\b",
     [("BNS", "124")], "acid"),

    # ── SC/ST atrocity (outside our DB but common query) ──
    (r"sc.?st|atrocit|caste.*viole|jaat.*(apmaan|insult)",
     [("BNS", "3")], "sc_st"),

    # ── General legal aid ──
    (r"legal aid|muft.*vakil|free.*lawyer|nalsa|dlsa|15100",
     [("BNSS", "341")], "legal_aid"),
]

# ── Suggestions per topic ────────────────────────────────────────────────
SUGGEST: dict[str, list[str]] = {
    "fir":               ["Zero FIR kya hoti hai?", "FIR ke baad kya hota hai?", "Agar police FIR likhne se mana kare to kya karein?"],
    "fir_refuse":        ["Magistrate se complaint kaise karein?", "Zero FIR kya hoti hai?", "Police complaint online kaise karein?"],
    "anticipatory_bail": ["Anticipatory bail ki process kya hai?", "Bail aur anticipatory bail me fark kya hai?", "Bail ke liye vakil zaruri hai kya?"],
    "default_bail":      ["Default bail kab milti hai?", "Chargesheet ka time limit kya hai?", "Remand kab tak ho sakta hai?"],
    "undertrial":        ["Undertrial ko kab bail milti hai?", "Jail me zyada time ho gaya to kya karein?"],
    "bail":              ["Anticipatory bail kab milti hai?", "Default bail kya hoti hai?", "Bailable aur non-bailable me fark kya hai?"],
    "arrest":            ["Giraftari par mere kya adhikar hain?", "Police kitne ghante me court me pesh karegi?", "Arrest hone par kya karein?"],
    "cheque":            ["Cheque bounce par notice kab tak bhejni hai?", "Notice ke baad complaint kab tak karni hai?", "Cheque bounce me saza kya hai?"],
    "murder":            ["Hatya aur galti se maut me kya fark hai?", "IPC 302 ab BNS me kaun sa section hai?", "Murder me bail milti hai kya?"],
    "robbery":           ["Robbery aur theft me kya fark hai?", "Loot me saza kya hai?"],
    "extortion":         ["Extortion ki FIR kaise karein?", "Dhamki de kar paisa mange to kya karein?"],
    "kidnapping":        ["Kidnapping ki FIR kaise karein?", "Kidnapping me saza kya hai?"],
    "sexual_offence":    ["Rape ki FIR kaise darj karein?", "Mahila thane me complaint kaise karein?", "POCSO kya hai?"],
    "molestation":       ["Eve teasing ki complaint kaise karein?", "Workplace harassment me kya karein?"],
    "stalking":          ["Stalking ki FIR kaise karein?", "Cyber stalking par kya kanoon hai?"],
    "voyeurism":         ["Privacy violate hone par kya karein?"],
    "dowry":             ["Dahej utpidan ki FIR kaise darj karein?", "Domestic violence me kya protection milta hai?", "498A me bail milti hai kya?"],
    "theft":             ["Chori ki FIR kaise karein?", "Chori me saza kya hai?"],
    "fraud":             ["Online fraud ho gaya to FIR kaise karein?", "Cyber crime helpline number kya hai?", "Cheating me saza kya hai?"],
    "assault":           ["Marpeet ki FIR kaise karein?", "Hurt aur grievous hurt me kya fark hai?"],
    "intimidation":      ["Dhamki milne par kya karein?", "Criminal intimidation me saza kya hai?"],
    "trespass":          ["Ghar me ghusne par kya karein?", "Trespass ki FIR kaise karein?"],
    "defamation":        ["Badnaami par case kaise karein?", "Defamation criminal hai ya civil?"],
    "driving":           ["Drunk driving me saza kya hai?", "Road accident me FIR kaise hoti hai?"],
    "rioting":           ["Danga me FIR kaise karein?"],
    "forgery":           ["Nakli dastavez banane par kya saza hai?", "Forgery ki FIR kaise karein?"],
    "conspiracy":        ["Criminal conspiracy kya hoti hai?", "IPC 120B ab BNS me kya hai?"],
    "attempt_murder":    ["Attempt to murder me saza kya hai?", "IPC 307 ab BNS me kya hai?"],
    "acid":              ["Acid attack me saza kya hai?", "Acid attack victim ke rights kya hain?"],
    "sc_st":             ["SC/ST Act me FIR kaise karein?", "Caste-based violence par kya karein?"],
    "legal_aid":         ["Free vakil kaise milega?", "DLSA se kaise sampark karein?", "NALSA helpline number kya hai?"],
    "default":           ["FIR kaise darj karein?", "Zamanat (bail) kaise milti hai?", "Cheque bounce par kya karein?",
                          "IPC 302 ab BNS me kaunsa section hai?", "Meri complaint nahi likhi ja rahi, kya karein?"],
}

# ── Scope detection ──────────────────────────────────────────────────────
_IN = re.compile(
    r"\b(fir|f\.i\.r|police|thana|bail|zamanat|jamanat|arrest|giraft|remand|chargesheet|bns|bnss|bsa|ipc|crpc|"
    r"section|dhara|cheque|check bounce|ni act|138|theft|chori|murder|hatya|qatl|fraud|cheating|dhokha|420|"
    r"dowry|dahej|court|magistrate|saza|punishment|offence|crime|complaint|shikayat|vakil|lawyer|evidence|"
    r"sakshya|legal aid|nalsa|dlsa|cyber|upi|kidnap|aghwa|rape|balatkar|molest|chhed|assault|marpeet|"
    r"robbery|loot|dacoity|extortion|vasool|defam|maanhaani|dhamki|threat|trespass|stalking|forgery|"
    r"jaalsaazi|acid|tezaab|rioting|danga|drunk driv|rash driv|attempt.*murder|conspiracy|saazish|"
    r"sc.?st|atrocit|pocso|domestic violence|gharelu hinsa|498a|302|307|376|420|506|hathkadi|"
    r"peshi|summon|warrant|investigation|jaanch|frd|chargesheet|challan)\b", re.I)

_OUT = re.compile(
    r"\b(zameen|jameen|land|property|plot|registry|mutation|khasra|khatauni|"
    r"divorce|talaq|custody|maintenance|alimony|guardianship|"
    r"will|vasiyat|inheritance|uttradhikar|succession|"
    r"tax|gst|itr|income tax|tds|"
    r"labour|salary|pf|esi|gratuity|minimum wage|"
    r"consumer|rti|"
    r"tenant|kiraya|landlord|rent agreement|"
    r"trademark|patent|copyright|"
    r"immigration|visa|passport|"
    r"company law|sebi|insolvency|nclt|"
    r"arbitration|contract|agreement|"
    r"motor vehicle|insurance claim|"
    r"environment|pollution|ngt)\b", re.I)

# ── Supported topics (for display) ──────────────────────────────────────
SUPPORTED_TOPICS = [
    "FIR darj karna / Zero FIR",
    "Bail (zamanat) — regular, anticipatory, default",
    "Arrest ke adhikar, remand, peshi",
    "Cheque bounce (NI Act s.138) — notice, deadline, complaint",
    "Murder, attempt to murder, culpable homicide",
    "Theft, robbery, dacoity, extortion",
    "Cheating, fraud, cyber/UPI fraud",
    "Kidnapping, abduction",
    "Sexual offences — rape, molestation, stalking, voyeurism",
    "Dowry, 498A, domestic violence",
    "Assault, hurt, grievous hurt",
    "Criminal intimidation, threats",
    "Trespass, defamation, forgery, rioting",
    "Acid attack",
    "Drunk/rash driving, road accidents",
    "SC/ST atrocity",
    "IPC ↔ BNS, CrPC ↔ BNSS, IEA ↔ BSA section mapping",
    "Free legal aid (DLSA/NALSA)",
]

OUT_MSG = (
    "Hamara platform **Police, FIR aur Criminal Law** ke in topics par jawab deta hai:\n"
    + "\n".join(f"• {t}" for t in SUPPORTED_TOPICS)
    + "\n\nAapka sawal in topics se bahar hai. Iske liye apne vakil ya **DLSA (free legal aid, NALSA helpline 15100)** se sampark karein."
)

# ── Hints (injected into evidence for the LLM) ──────────────────────────
HINTS = [
    (r"zero fir",
     "NOTE: 'Zero FIR' is the popular name for BNSS s.173(1): information about a cognizable offence can be given to "
     "any officer in charge of a police station 'irrespective of the area where the offence is committed'."),
    (r"default bail|statutory bail",
     "NOTE: 'Default bail' = release on bail when the police do not finish investigation within the "
     "time limit in the proviso to BNSS s.187(3) (see also s.479 for undertrial detention)."),
    (r"fir.*(nahi|not|refuse|mana)|police.*(nahi|not|refuse|mana).*likh",
     "NOTE: If the police refuse to register FIR, the person can send the complaint in writing and by post to the "
     "Superintendent of Police (s.175), or file a complaint directly before a Magistrate (s.223 BNSS, earlier CrPC s.190/200)."),
    (r"cyber|online|upi|internet",
     "NOTE: For cyber crimes, victims can also file complaints at cybercrime.gov.in (National Cyber Crime Reporting Portal) "
     "or call helpline 1930. The substantive offence (cheating, fraud) falls under BNS; IT Act provisions are outside this platform's scope."),
    (r"legal aid|free.*lawyer|muft.*vakil|nalsa|dlsa",
     "NOTE: Free legal aid is available under Legal Services Authorities Act 1987 via DLSA (District Legal Services Authority). "
     "NALSA helpline: 15100. Eligible: women, children, SC/ST, disabled, industrial workmen, persons in custody, and anyone with "
     "annual income below the state threshold."),
    (r"sc.?st|atrocit|caste",
     "NOTE: SC/ST (Prevention of Atrocities) Act 1989 is a special law outside this platform's core database. "
     "FIR under this Act is registered at a regular police station. For specifics of the Act, consult a lawyer or DLSA."),
]


def hint_for(query: str) -> str:
    return " ".join(h for rx, h in HINTS if re.search(rx, query or "", re.I))


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
    return SUGGEST.get(topic_key(query) or "default", SUGGEST["default"])


_FIXED = [(r"zero\s*fir", {
    "hi": ("Zero FIR ka matlab: FIR kisi bhi police station me darj ho sakti hai, chahe ghatna uske ilaake me hui ho ya nahi. "
           "Aisa nahi hai ki 'FIR nahi likhi jaati'.\n\n"
           "📌 Kanoon: BNSS section 173(1) — cognizable offence ki jaankari 'irrespective of the area where the offence is committed' "
           "kisi bhi police station ke officer in charge ko orally ya electronic communication se di ja sakti hai.\n"
           "⚖️ Process: orally di to officer use likhega, aapko padh kar sunayega, aur aapke sign honge (173(1)(i)).\n"
           "ℹ️ Practice me aisi FIR baad me sambandhit thane ko bheji jaati hai — ye 173(1) ke text me nahi likha, vakil ya police se confirm karein."),
    "en": ("Zero FIR means an FIR can be registered at ANY police station, whether or not the offence happened in its area.\n\n"
           "📌 Law: BNSS s.173(1) — information about a cognizable offence, 'irrespective of the area where the offence is committed', "
           "may be given orally or electronically to an officer in charge of a police station.\n"
           "⚖️ Process: if given orally, the officer reduces it to writing, reads it over to you, and you sign it (s.173(1)(i)).\n"
           "ℹ️ In practice it is later sent to the police station with jurisdiction — that is not in the text of s.173(1); confirm with a lawyer or the police.")})]


def fixed_answer(query: str, hinglish: bool):
    """Hand-checked answer for popular terms the model keeps getting wrong. None if no match."""
    for rx, ans in _FIXED:
        if re.search(rx, query or "", re.I):
            return ans["hi" if hinglish else "en"]
    return None


def scope_info() -> dict:
    """Returns supported topics list and example questions — for frontend welcome screen / API."""
    examples = [
        "FIR kaise darj karein?",
        "Zero FIR kya hoti hai?",
        "Bail kaise milti hai?",
        "Cheque bounce par kya karein?",
        "IPC 302 ab BNS me kya hai?",
        "Arrest hone par mere kya rights hain?",
        "Online fraud ho gaya, kya karein?",
        "Dahej utpidan ki complaint kaise karein?",
    ]
    return {"domain": "Police, FIR aur Criminal Law", "topics": SUPPORTED_TOPICS, "examples": examples}