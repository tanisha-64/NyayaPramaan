"""
TrustAgent Step 1 — extracts PLAIN, markdown-free claims (not from the raw
markdown-table-heavy draft directly, which breaks JSON parsing). Returns
(claims, success_flag) so the caller can distinguish extraction-failure
from genuinely-zero-claims.

Table rows are flattened into plain "cell; cell" lines rather than deleted: the claims inside a table (often the
evidence list itself) must be verified like any other statement.
"""
from ai_core.llm_gateway import call_llm
import json
import re

MAX_CLAIMS = 10
MAX_ANSWER_CHARS = 6000


def flatten_markdown(draft_answer: str) -> str:
    lines = []
    for line in (draft_answer or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue                           # the |---|---| separator row carries no claim
            lines.append("; ".join(c for c in cells if c) + ".")
        else:
            lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"[#*_`]", "", text)[:MAX_ANSWER_CHARS]


def extract_claims(draft_answer: str) -> tuple[list[str], bool]:
    plain_text = flatten_markdown(draft_answer)

    prompt = f"""Extract every distinct factual claim from this answer that matters to a lawyer (parties, dates, amounts, section numbers, holdings, evidence items, page references), at most {MAX_CLAIMS}. Write each as a simple single-sentence string with NO markdown, NO pipes, NO special characters. Return ONLY a JSON array of strings.

Answer: {plain_text}

JSON array:"""
    try:
        raw = call_llm("groq/openai/gpt-oss-20b", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        claims = json.loads(cleaned)
        if isinstance(claims, list):
            claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()][:MAX_CLAIMS]
        if isinstance(claims, list) and claims:
            return claims, True
        return [], True  # genuinely no claims found -- not an error
    except Exception:
        return [], False  # extraction infrastructure failed
