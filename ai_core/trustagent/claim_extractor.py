"""
TrustAgent Step 1 -- Claim Extraction
Splits a draft answer into individual, independently-verifiable claims.
"""
from ai_core.llm_gateway import call_llm
import json
import re

def extract_claims(draft_answer: str) -> list[str]:
    prompt = f"""List each individual factual/legal claim in the answer below as a JSON array of strings. Return ONLY the JSON array, nothing else.

Answer: {draft_answer}

JSON array:"""
    # raw = call_llm("gemini/gemini-3.6-flash", prompt)
    raw = call_llm("groq/openai/gpt-oss-20b", prompt)
    # Gemini sometimes wraps JSON in ```json ... ``` -- strip that if present
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(cleaned)
    except Exception:
        return [draft_answer]