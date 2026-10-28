"""scripts/ingest_ni_act.py (NEW). Loads the Negotiable Instruments Act, 1881 PDF (India Code) into `statute_sections`
as act='NI', verbatim.   python scripts/ingest_ni_act.py --pdf data/NI.pdf --url <India Code PDF link> [--dry-run]"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.ingest_statutes import parse  # noqa: E402

NAME = "Negotiable Instruments Act, 1881"


def build(pages: list[str]) -> dict:
    s = parse(pages, strict=True)
    full = "\n".join(pages)
    if "148" not in s:   # the parser leaves s.148 glued to the end of s.147 - split it out
        t = s["147"]["text"]
        m = re.search(r"\]?\s*1?\s*\[148\.", t)
        if m:
            s["148"] = {"section": "148", "heading": "Power of Appellate Court to order payment pending appeal against conviction",
                        "page": s["147"]["page"], "text": t[m.start():].strip(" ]")}
            s["147"]["text"] = t[:m.start()].strip()
    for k in ("147", "148"):   # cut the page-footer / schedule noise
        if k in s:
            s[k]["text"] = re.split(r"\s*IndiaCode\s+SCHEDULE", s[k]["text"])[0].strip()
    if "6" not in s:         # s.6 (Cheque) is missed by the parser (its number is in footnote style)
        m = re.search(r"\[?6\. “Cheque\.”—.*?(?=\n\s*(?:1\s*)?\[?7\. )", full[full.find("PRELIMINARY", 3000):], re.S)
        if m:
            s["6"] = {"section": "6", "heading": "Cheque", "page": None, "text": re.sub(r"\s+", " ", m.group(0)).strip()}
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True); ap.add_argument("--url", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    import pymupdf
    secs = build([p.get_text() for p in pymupdf.open(a.pdf)])
    need = ["138", "139", "140", "141", "142", "142A", "143", "143A", "144", "145", "146", "147", "148"]
    miss = [k for k in need if k not in secs]
    print(f"NI: {len(secs)} sections parsed; chapter XVII missing: {miss}")
    print(secs["138"]["text"][:200])
    if miss or a.dry_run:
        sys.exit(1 if miss else 0)
    from ai_core.rag.vector_store import get_supabase_client
    rows = [{**v, "act": "NI", "act_name": NAME, "source_url": a.url} for v in secs.values()]
    c = get_supabase_client()
    for i in range(0, len(rows), 100):
        c.table("statute_sections").upsert(rows[i:i + 100], on_conflict="act,section").execute()
    print("loaded", len(rows))


if __name__ == "__main__":
    main()