import re
OLD2NEW = {"IPC": "BNS", "CrPC": "BNSS", "IEA": "BSA"}
NEW2OLD = {v: k for k, v in OLD2NEW.items()}
CUTOFF = "1 July 2024"

def _norm(act):
    a = act.strip().upper().replace("CRPC", "CrPC")
    return {"CRPC": "CrPC"}.get(a, a)

def _top(sec):
    return re.match(r"\d+[A-Z]*", sec.strip().upper()).group(0)

def lookup(sb, act, section):
    """act: IPC/CrPC/IEA/BNS/BNSS/BSA. Returns dict for the answer layer."""
    act = "CrPC" if act.lower() == "crpc" else act.upper()
    sec = _top(section)
    if act in OLD2NEW:   # old -> new
        q = sb.table("section_map").select("*").eq("old_act", act)
        rows = q.or_(f"old_section.eq.{sec},old_section.like.{sec}(%)").execute().data
        kind = "old_to_new"
    elif act in NEW2OLD:  # new -> old
        rows = (sb.table("section_map").select("*").eq("new_act", act)
                .eq("new_top", sec).execute().data)
        kind = "new_to_old"
    else:
        return None
    if not rows:
        return {"found": False, "kind": kind, "note":
            f"{act} {sec} ka comparison table me koi row nahi mila (omitted/repealed ya table me nahi). "
            "Official gazette / India Code se confirm karein."}
    return {"found": True, "kind": kind, "rows": rows, "note":
        f"{CUTOFF} se pehle ke offences par purana law (IPC/CrPC/IEA) hi lagta hai; "
        "uske baad ke par naya. Source: comparison table (non-official), legal advice nahi."}