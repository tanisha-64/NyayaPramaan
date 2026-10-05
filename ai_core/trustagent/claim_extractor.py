"""
TrustAgent Step 1 — extracts PLAIN, markdown-free claims (not from the raw
markdown-table-heavy draft directly, which breaks JSON parsing). Returns
(claims, success_flag) so the caller can distinguish extraction-failure
from genuinely-zero-claims.
"""
from ai_core.llm_gateway import call_llm
import json
import re


def extract_claims(draft_answer: str) -> tuple[list[str], bool]:
    # Strip markdown tables/formatting before sending to the LLM -- raw
    # pipe-characters and table syntax were causing JSON-parse failures.
    plain_text = re.sub(r"\|.*\|", "", draft_answer)
    plain_text = re.sub(r"[#*_`]", "", plain_text)
    plain_text = plain_text[:3000]

    prompt = f"""Extract 3-6 short, PLAIN factual claims from this answer, each as a simple single-sentence string with NO markdown, NO pipes, NO special characters. Return ONLY a JSON array of strings.

Answer: {plain_text}

JSON array:"""
    try:
        raw = call_llm("groq/openai/gpt-oss-20b", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        claims = json.loads(cleaned)
        if isinstance(claims, list) and claims:
            return claims, True
        return [], True  # genuinely no claims found -- not an error
    except Exception:
        return [], False  # extraction infrastructure failed
