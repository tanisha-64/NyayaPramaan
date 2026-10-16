"""ai_core/rag/section_map.py (FULL REPLACEMENT) - old<->new law lookup from table `section_map`."""
import re

OLD2NEW = {"IPC": "BNS", "CRPC": "BNSS", "IEA": "BSA"}
NEW2OLD = {"BNS": "IPC", "BNSS": "CrPC", "BSA": "IEA"}
CUTOFF = "1 July 2024"


def _top(sec: str) -> str:
    m = re.match(r"\d+[A-Z]*", (sec or "").strip().upper())
    return m.group(0) if m else ""


def lookup(sb, act: str, section: str):
    """Rows mapping act/section to the other law, or [] (section omitted/repealed/not in the table). Never raises."""
    act, sec = (act or "").upper(), _top(section)
    try:
        t = sb.table("section_map").select("*")
        if act in OLD2NEW:
            oa = NEW2OLD[OLD2NEW[act]]
            rows = sb.table("section_map").select("*").eq("old_act", oa).eq("old_section", sec).execute().data or []
            rows += sb.table("section_map").select("*").eq("old_act", oa).like("old_section", f"{sec}(*)").execute().data or []
        elif act in NEW2OLD:
            rows = t.eq("new_act", act).eq("new_top", sec).execute().data or []
        else:
            return []
    except Exception:  # noqa: BLE001
        return []
    seen, out = set(), []
    for r in rows:
        k = (r["new_act"], r["new_section"], r["old_section"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def mapping_note(sb, act: str, section: str, hi: bool = True) -> str:
    """Short text appended to an explicit-lookup answer. For an OLD act with no mapping row, explains why."""
    act = (act or "").upper()
    rows = lookup(sb, act, section)
    old = act in OLD2NEW
    if not rows:
        if old:
            return (f"\n\n🔁 {act} {section}: naye kanoon ({OLD2NEW[act]}) ki comparison table me iska seedha equivalent nahi mila "
                    "(section hata diya gaya ho sakta hai ya repeal ho chuka ho). Pakka karne ke liye India Code dekhein."
                    if hi else f"\n\n🔁 {act} {section}: no direct {OLD2NEW[act]} equivalent in the comparison table "
                    "(it may have been omitted or already repealed). Confirm on India Code.")
        return ""
    lines = []
    for r in rows[:6]:
        a = f"{r['old_act']} {r['old_section']}" if r["old_section"] else "(new provision)"
        b = f"{r['new_act']} {r['new_section']}"
        lines.append(f"• {a} → {b}: {r['subject']} [{r['change_type']}]" if old else f"• {b} ← {a} [{r['change_type']}]")
    tail = (f"{CUTOFF} se pehle ke offences par purana kanoon hi lagta hai." if hi
            else f"Offences before {CUTOFF} are still governed by the old law.")
    return "\n\n🔁 " + ("Naya/purana kanoon:" if hi else "Old ↔ new law:") + "\n" + "\n".join(lines) + "\n" + tail