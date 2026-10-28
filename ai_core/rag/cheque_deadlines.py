"""ai_core/rag/cheque_deadlines.py (NEW) - deterministic NI Act s.138/142 deadline calculator. No LLM, no guessing.
Rules (text of the Act): s.138 proviso (a) present within 6 months of the cheque date or its validity, whichever is earlier;
(b) written notice within 30 days of receiving the bank's return information; (c) drawer has 15 days from receiving the
notice to pay; s.142(1)(b) complaint within one month of the cause of action (the day after those 15 days end),
late complaint only with 'sufficient cause'. First day is excluded (General Clauses Act s.9) - dates can still be off
by a day, so the tool always says: file early."""
import calendar
from datetime import date, timedelta

VALIDITY_MONTHS = 3   # usual cheque validity (RBI/bank practice) - NOT in the Act; user may override


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _step(key, label, due, rule, today, ok=None, note=""):
    st = ("done" if ok else "missed" if ok is False else "passed" if today > due else "open" if due else "info")
    return {"key": key, "label": label, "date": due.isoformat(), "rule": rule, "status": st, "note": note,
            "days_left": (due - today).days}


def compute(drawn: date, bank_info: date, presented: date | None = None, notice_sent: date | None = None,
            notice_received: date | None = None, validity_months: int = VALIDITY_MONTHS, today: date | None = None) -> dict:
    """drawn = date written on the cheque; bank_info = date you got the return memo/information from the bank."""
    today = today or date.today()
    steps, warn = [], []
    valid_to = min(add_months(drawn, 6), add_months(drawn, validity_months))
    ok_p = None if presented is None else presented <= valid_to
    steps.append(_step("presentation", "Cheque bank me lagane ki last date", valid_to,
                       "s.138 proviso (a): cheque date se 6 mahine ya validity, jo pehle ho", today, ok_p,
                       f"Validity {validity_months} mahine maani gayi (bank niyam; Act me nahi). Cheque par likhi validity dekhein."))
    if ok_p is False:
        warn.append("Cheque late present hua - s.138 ka case kamzor ho sakta hai. Vakil se turant poochhein.")
    n_last = bank_info + timedelta(days=30)
    steps.append(_step("notice", "Legal notice bhejne ki last date", n_last,
                       "s.138 proviso (b): bank se return ki jaankari milne ke 30 din ke andar, likhit notice", today,
                       None if notice_sent is None else notice_sent <= n_last))
    if notice_sent and notice_sent > n_last:
        warn.append("Notice 30 din ke baad bheji gayi lagti hai - ye case ke liye gambhir dikkat hai.")
    recv, tentative = notice_received or notice_sent, notice_received is None and notice_sent is not None
    if recv:
        pay_last = recv + timedelta(days=15)
        steps.append(_step("payment", "Drawer ke paise dene ki last date", pay_last,
                           "s.138 proviso (c): notice milne ke 15 din ke andar", today, None,
                           "Notice milne ki tareekh abhi 'bheji gayi tareekh' maani gayi - post/AD card se asli tareekh daalein."
                           if tentative else ""))
        cause = pay_last + timedelta(days=1)
        c_last = add_months(cause, 1)
        steps.append(_step("cause", "Shikayat ka adhikar (cause of action) shuru", cause,
                           "s.138 proviso (c) ke 15 din khatam hone ke agle din", today, None))
        steps.append(_step("complaint", "Court me complaint file karne ki last date", c_last,
                           "s.142(1)(b): cause of action se ek mahine ke andar", today, None,
                           "Late hone par court 'sufficient cause' dekhkar maaf kar sakta hai (s.142(1)(b) proviso), guarantee nahi."))
        if today > c_last:
            warn.append("Complaint ki date nikal chuki hai. Court se deri maaf karne ki arzi (sufficient cause) ke liye vakil se milein.")
    else:
        warn.append("Notice bhejne/milne ki tareekh daalein, tab payment aur complaint ki dates nikalengi.")
    warn.append("Tareekhein ek din aage-peeche ho sakti hain (din gine jaane ke niyam, chhutti). Hamesha 2-3 din pehle file karein "
                "aur vakil se confirm karein. Yeh kanooni salah nahi hai.")
    return {"steps": steps, "warnings": warn}


QUICK_FACTS = [  # all verified against the NI Act PDF (as amended up to Act 20 of 2018)
    {"text": "Saza: 2 saal tak ki jail, ya cheque amount ka 2 guna tak jurmana, ya dono.", "section": "138"},
    {"text": "Cheque dene wale ne maana ki paise ke badle diya tha - ye maan liya jata hai jab tak wo ulta sabit na kare.", "section": "139"},
    {"text": "Complaint likhit hogi, payee/holder in due course karega, Magistrate (JMFC/Metropolitan) ke court me.", "section": "142"},
    {"text": "Court wahi jahan payee ka khata wali branch hai (collection) ya jahan drawer ki bank branch hai (seedhe present).", "section": "142(2)"},
    {"text": "Court mukadme me drawer ko cheque amount ka 20% tak interim compensation dene ka order de sakta hai.", "section": "143A"},
    {"text": "Appeal me drawer ko fine/compensation ka kam se kam 20% jama karna pad sakta hai.", "section": "148"},
    {"text": "Ye apradh compoundable hai - dono pakshon ki sahmati se samjhauta ho sakta hai.", "section": "147"},
]