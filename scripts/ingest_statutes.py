"""scripts/ingest_statutes.py. Loads a statute PDF into `statute_sections`, verbatim.
  python -m pip install pypdf pymupdf
  python scripts/ingest_statutes.py --act BNS --name "Bharatiya Nyaya Sanhita, 2023" --pdf scripts/BNS.pdf \
      --url <link of the page/PDF you downloaded it from> --expected 358 [--dry-run] [--strict for IPC]
Refuses to load when sections are missing (completeness check) unless --force."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, so `ai_core` imports work

_PRE = r"^\s*(?:\d{1,2}\[\s*)?"                      # amended sections start like "4[53A. Heading.—"
_START = re.compile(_PRE + r"(\d{1,3})([A-Z]{0,2})\.\s*\S")
_HEAD = re.compile(_PRE + r"(\d{1,3}[A-Z]{0,2})\.?\s*([A-Z“][^()\n]{2,200}?)(?:\.\s*$|\.\s*[—–-])")
_FOOT = re.compile(r"^\s*\d{1,3}\.\s*(Subs|Ins|Rep|Omitted|The words|Added|See|Clause|Re-numbered|Renumbered)", re.I)
_DASH = re.compile(_PRE + r"(\d{1,3})([A-Z]{0,2})\.?\s*[A-Z“][^\n]{2,200}?\.\s*[—–-]")  # "53. Punishments.—" (dot sometimes missing)
_NUMSTART = re.compile(_PRE + r"\d{1,3}[A-Z]{0,2}\.?\s*[A-Z“]")
_NOISE = re.compile(r"GAZETTE OF INDIA|^\s*\d+\s*$|^\s*\[?PART\b|Bare Act is a government source", re.I)


def _join_wrapped(text: str) -> list[str]:
    """A long heading can wrap: '87. Act not intended to cause death...\nconsent.—Nothing' -> one line."""
    ls, out, i = text.split("\n"), [], 0
    while i < len(ls):
        l = ls[i]
        if (i + 1 < len(ls) and _NUMSTART.match(l) and not _DASH.match(l) and not _FOOT.match(l)
                and re.match(r"^[^\n]{0,120}?\.\s*[—–-]", ls[i + 1])):
            l, i = l.rstrip() + " " + ls[i + 1], i + 1
        out.append(l)
        i += 1
    return out


def parse(pages: list[str], strict: bool = False) -> dict:
    """strict=True (annotated IPC copies): a section starts only on 'N. Heading.—' lines, so footnotes never count."""
    heads, secs, last, cur = {}, {}, 0, None
    for pno, text in enumerate(pages, 1):
        for line in (_join_wrapped(text) if strict else text.split("\n")):
            h = _HEAD.match(line)
            if h:
                heads.setdefault(h.group(1), h.group(2).strip())
            if _FOOT.match(line):                                 # footnote of an amended law, not statute text
                continue
            m = (_DASH if strict else _START).match(line)
            if m:
                n, suf = int(m.group(1)), m.group(2)
                if n == 1 and not suf and last > 5:          # table of contents ended -> restart on the real body
                    secs, last = {}, 0
                gap = last + 1 < n <= last + (60 if strict else 4) and (strict or _HEAD.match(line))  # repealed/omitted in between
                if (not suf and n == last + 1) or (suf and n == last) or (not suf and gap):
                    last, cur = n, m.group(1) + suf
                    secs[cur] = {"page": pno, "lines": [line.strip()]}
                    continue
            if strict and re.match(r"^\s*\d{1,3}\.\s", line):       # numbered line that is not a section = footnote
                continue
            if cur and not _NOISE.search(line):
                secs[cur]["lines"].append(line.strip())
    return {k: {"section": k, "heading": heads.get(k), "page": v["page"],
                "text": re.sub(r"\s+", " ", " ".join(v["lines"])).strip()} for k, v in secs.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--pdf", required=True); ap.add_argument("--url", required=True)
    ap.add_argument("--expected", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--strict", action="store_true", help="use for IPC (headings written as 'N. Heading.—')")
    a = ap.parse_args()
    try:  # PyMuPDF is much faster than pypdf on big PDFs
        import pymupdf
        pages = [p.get_text() for p in pymupdf.open(a.pdf)]
    except ImportError:
        from pypdf import PdfReader
        pages = [p.extract_text() or "" for p in PdfReader(a.pdf).pages]
    secs = parse(pages, a.strict)
    nums = {int(re.match(r"\d+", k).group()) for k in secs}
    missing = [n for n in range(1, a.expected + 1) if n not in nums]
    print(f"{a.act}: {len(secs)} sections parsed, expected {a.expected}, missing {missing[:80]}{'...' if len(missing) > 80 else ''}")
    for k in ("1", "103", "303"):
        if k in secs:
            print(f"--- {a.act} {k} ({secs[k]['heading']}) p.{secs[k]['page']}:\n{secs[k]['text'][:300]}")
    if (missing and not a.force) or a.dry_run:
        sys.exit(1 if missing and not a.force else 0)
    from ai_core.rag.vector_store import get_supabase_client
    rows = [{**v, "act": a.act, "act_name": a.name, "source_url": a.url} for v in secs.values()]
    client = get_supabase_client()
    for i in range(0, len(rows), 100):
        client.table("statute_sections").upsert(rows[i:i + 100], on_conflict="act,section").execute()
    print("loaded", len(rows))


if __name__ == "__main__":
    main()