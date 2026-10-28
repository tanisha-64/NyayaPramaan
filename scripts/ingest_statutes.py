"""scripts/ingest_statutes.py (NEW). Loads an OFFICIAL India Code PDF into `statute_sections`, verbatim.
  pip install pypdf
  python scripts/ingest_statutes.py --act BNS --name "Bharatiya Nyaya Sanhita, 2023" --pdf bns.pdf \
      --url <PDF link copied from the Act's page on indiacode.nic.in> --expected 358 [--dry-run]
Refuses to load when sections are missing (completeness check) unless --force."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, so `ai_core` imports work

_PRE = r"^\s*(?:\d{1,2}\[\s*)?"                      # amended sections start like "4[53A. Heading.—"
_START = re.compile(_PRE + r"(\d{1,3})([A-Z]{0,2})\.\s*\S")
_HEAD = re.compile(_PRE + r"(\d{1,3}[A-Z]{0,2})\.?\s*([A-Z“][^()\n]{2,200}?)(?:\.\s*$|\.\s*[—–-])")
_FOOT = re.compile(r"^\s*\d{1,3}\.\s*(Subs|Ins|Rep|Omitted|The words|Added|See|Clause|Re-numbered|Renumbered)\b", re.I)
_DASH = re.compile(_PRE + r"(\d{1,3})([A-Z]{0,2})\.?\s*[A-Z“][^\n]{2,200}?\.\s*[—–-]")  # "53. Punishments.—" (dot sometimes missing)
_NUMSTART = re.compile(_PRE + r"\d{1,3}[A-Z]{0,2}\.?\s*[A-Z“]")
_NOISE = re.compile(r"GAZETTE OF INDIA|^\s*\d+\s*$|^\s*\[?PART\b|Bare Act is a government source"
                     r"|EXTRAORDINARY|PUBLISHED BY AUTHORITY|REGISTERED NO|MINISTRY OF LAW|Legislative Department"
                     r"|^\s*CG-DL|assent of the President|hereby published for general information"
                     r"|^\s*xxxGID", re.I)
_ALLCAPS = re.compile(r"^[A-Z0-9][A-Z0-9 ,.\-—–'\"()/]{1,}$")  # a PART/CHAPTER title line between sections, e.g.
                                                                 # "PARTIV" or "PRODUCTION AND EFFECT OF EVIDENCE"
_RULE = re.compile(r"^[ \t]{10,}$|^_{10,}$")  # page-bottom footnotes/border start with a blank or underscore rule line
_GAZETTE = re.compile(r"GAZETTE OF INDIA", re.I)
_PAGE_FOOT = re.compile(r"^\s*\d{1,4}\s*$|^\s*Sec\.\s*\d+\]\s*$|^\s*\[?Part\b", re.I)


def _strip_gazette_margins(lines: list[str]) -> list[str]:
    """Some official PDFs (two-column Gazette layout) print each section's heading in a side-margin column, not
    inline. Text extraction dumps that whole margin column as a block of short lines right before the page's
    'GAZETTE OF INDIA ...' footer. Drop that block (and the footer/page-number lines around it) so it never
    bleeds into the body of whichever section happens to be open at that point."""
    out = list(lines)
    gidx = next((i for i, l in enumerate(out) if _GAZETTE.search(l)), None)
    if gidx is None:
        return out
    j = gidx - 1
    while j >= 0 and _PAGE_FOOT.match(out[j]):
        out[j], j = "", j - 1
    while j >= 0 and 0 < len(out[j].strip()) <= 20 and not (_START.match(out[j]) or _DASH.match(out[j])):
        out[j], j = "", j - 1
    out[gidx] = ""
    return out


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
    toc_reset_done = False
    for pno, text in enumerate(pages, 1):
        in_footnotes = False
        page_lines = _strip_gazette_margins(text.split("\n"))
        for line in (_join_wrapped("\n".join(page_lines)) if strict else page_lines):
            if _RULE.match(line):            # everything below this rule line, on this page, is a footnote
                in_footnotes = True
                continue
            if in_footnotes:
                continue
            if not (_DASH if strict else _START).match(line):
                # a footnote-reference digit sometimes glues onto the number with no bracket: "1145." for "145."
                stripped = re.sub(r"^(\s*)\d", r"\1", line, count=1)
                m0 = (_DASH if strict else _START).match(stripped)
                if m0 and not m0.group(2) and int(m0.group(1)) == last + 1:
                    line = stripped
            h = _HEAD.match(line)
            if h:
                heads.setdefault(h.group(1), h.group(2).strip())
            if _FOOT.match(line):                                 # footnote of an amended law, not statute text
                continue
            m = (_DASH if strict else _START).match(line)
            if m:
                n, suf = int(m.group(1)), m.group(2)
                if n == 1 and not suf and last > 5 and not toc_reset_done:  # TOC ended -> restart on the real body (once only)
                    secs, last, toc_reset_done = {}, 0, True
                gap = last + 1 < n <= last + (60 if strict else 4) and (strict or _HEAD.match(line))  # repealed/omitted in between
                if (not suf and n == last + 1) or (suf and n == last) or (not suf and gap):
                    last, cur = n, m.group(1) + suf
                    secs[cur] = {"page": pno, "lines": [line.strip()]}
                    continue
            if strict and re.match(r"^\s*\d{1,3}\.\s", line):       # numbered line that is not a section = footnote
                continue
            if cur and not _NOISE.search(line) and not _ALLCAPS.match(line.strip()):
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
    from pypdf import PdfReader
    try:  # PyMuPDF is much faster than pypdf on big PDFs
        import pymupdf
        pages = [p.get_text() for p in pymupdf.open(a.pdf)]
    except ImportError:
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