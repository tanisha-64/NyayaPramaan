"""grounding.py (NEW) -> ai_core/formatting/grounding.py
Deterministic validator: drops every sentence that states a number (section, days, amount, year, phone) or names
an Act/Code/Tribunal that is NOT present in the evidence. Cheap, no LLM, can only remove, never invent."""
import re

_NUM = re.compile(r"\d+")
_ACT = re.compile(r"\b(?:[A-Z][A-Za-z.&']+\s+){0,4}(?:Act|Code|Sanhita|Adhiniyam|Tribunal|Commission)\b")
# helplines verified & used in our prompt + facts the prompt itself states (BNS 2023 in force 1 July 2024, IPC 1860)
ALLOWED = {"112", "181", "1930", "1098", "15100", "1", "2023", "2024", "1860"}


def ground_answer(answer: str, evidence: str = "", allowed=ALLOWED) -> str:
    ev = (evidence or "").lower()
    ev_nums = set(_NUM.findall(ev)) | set(allowed)
    lines = []
    for line in (answer or "").split("\n"):
        keep = []
        for s in re.split(r"(?<=[.!?।])\s+", line):
            body = re.sub(r"^\s*(\d+[.)]|[•\-])\s*", "", s)
            acts = [m.group(0).strip().lower() for m in _ACT.finditer(body)]
            if set(_NUM.findall(body)) <= ev_nums and all(a in ev for a in acts):
                keep.append(s)
        lines.append(" ".join(keep).strip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()