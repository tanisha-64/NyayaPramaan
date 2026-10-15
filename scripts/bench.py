"""scripts/bench.py. Time + accuracy check against a running backend (local or live).
  PowerShell:  $env:TOKEN="<access token from the browser>"; $env:BASE_URL="http://localhost:8000"
               $env:CASE_ID="<uploaded case id>"   # optional: also tests that document
               python scripts/bench.py
Accuracy = the answer holds every expected word AND every number in it is backed by a source (or is an allowed helpline)."""
import os
import re
import statistics
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai_core.formatting.grounding import ALLOWED  # noqa: E402

BASE, TOKEN, CASE = os.getenv("BASE_URL", "http://localhost:8000"), os.environ["TOKEN"], os.getenv("CASE_ID")
H = {"Authorization": f"Bearer {TOKEN}"}
# (question, words that MUST appear in the answer, use the uploaded document?)  <- edit/add your own
CASES = [
    ("IPC 302", ["murder", "death"], False), ("BNS section 103", ["murder", "life"], False),
    ("IPC 420", ["cheats", "seven years"], False), ("BNS 999", ["not in our verified"], False),
    ("What is love?", ["legal"], False), ("IPC 302, BNS 103", ["302", "103"], False),
    ("chori ki saza kya hai", ["theft"], False),
    ("judgment ki date kya hai", ["19"], True), ("is document me cheque ka zikr hai?", ["no supporting evidence"], True),
]
nums = lambda t: set(re.findall(r"\d+", t or ""))
rows = []
for q, must, doc in CASES:
    if doc and not CASE:
        continue
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{BASE}/chat/ask", headers=H, json={"query": q, "case_id": CASE if doc else None}, timeout=120).json()
    except Exception as e:  # noqa: BLE001
        r = {"answer": f"ERROR {type(e).__name__}", "sources": []}
    sec = time.perf_counter() - t0
    ans, src = r.get("answer", ""), r.get("sources") or []
    backed = nums(" ".join((s.get("excerpt") or "") + (s.get("name") or "") for s in src)) | ALLOWED | nums(q)
    ok_words, ok_nums = all(w.lower() in ans.lower() for w in must), nums(ans) <= backed
    rows.append((q[:38], round(sec, 1), r.get("verdict_state", "-"), len(src), ok_words, ok_nums))
    print(f"{q[:38]:38} {sec:6.1f}s  {str(r.get('verdict_state', '-')):20} sources={len(src):2}  words={'OK' if ok_words else 'MISS'}  numbers={'OK' if ok_nums else 'UNBACKED'}")
if CASE:
    d = requests.get(f"{BASE}/chat/debug/case/{CASE}", headers=H).json()
    print("document:", d.get("case_text_chars"), "chars,", d.get("chunks_in_db"), "chunks ->", (d.get("chunks_in_db") or 0) * 5, "KB approx in DB")
ts = sorted(r[1] for r in rows)
if ts:
    print(f"\nanswers {len(rows)} | accurate {sum(r[4] and r[5] for r in rows)}/{len(rows)} | median {statistics.median(ts)}s | slowest {ts[-1]}s")