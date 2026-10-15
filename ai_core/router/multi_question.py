"""multi_question.py (NEW) -> ai_core/router/multi_question.py
Splits one message holding several questions into separate questions and merges the separate answers."""
import re

_CUE = re.compile(r"\b(kya|kaise|kitn\w*|kab|kaun\w*|kyu\w*|what|how|when|who|why|which|saza|punishment|section|ipc|bnss|bns|bsa)\b", re.I)
_REF = re.compile(r"\b(ipc|bnss|bns|bsa|crpc)\b\s*\d", re.I)


def split_questions(q: str, limit: int = 4) -> list[str]:
    """['IPC 56', 'IPC 302 ka BNS kya hai'] for 'IPC 56, IPC 302 ka BNS kya hai'; [q] when it is one question."""
    q = (q or "").strip()
    out = []
    for p in (x.strip(" ,.;") for x in re.split(r"\?+\s*|\n+|;", q)):
        if not p:
            continue
        subs = [s.strip() for s in p.split(",")]
        parts = subs if len(subs) > 1 and all(len(s.split()) >= 2 and _CUE.search(s) for s in subs) else [p]
        for s in parts:
            if out and len(s.split()) < 3 and not _REF.search(s):   # a fragment such as "explain briefly"
                out[-1] += " " + s
            else:
                out.append(s)
    return out[:limit] if len(out) > 1 else [q]


def merge_answers(questions: list[str], results: list[dict], partial_state: str) -> dict:
    """One response: every answer under its question, sources de-duplicated, verdict = common state or partial."""
    blocks, sources, seen, states, sugg = [], [], set(), set(), []
    for q, r in zip(questions, results):
        blocks.append(f"\u2753 {q}\n{r.get('answer') or r.get('reason') or ''}".strip())
        states.add(r.get("verdict_state"))
        for s in r.get("sources") or []:
            k = (s.get("name"), s.get("url"), s.get("page"))
            if k not in seen:
                seen.add(k)
                sources.append(s)
        sugg += [x for x in (r.get("suggestions") or []) if x not in sugg]
    return {"answer": "\n\n\u2014\u2014\u2014\n\n".join(blocks), "conclusion": None,
            "verified": all(r.get("verified") for r in results), "sources": sources, "usefulness": "medium",
            "routing_label": "MULTI", "claim_verdicts": [], "suggestions": sugg[:3], "multi": True,
            "verdict_state": states.pop() if len(states) == 1 else partial_state}