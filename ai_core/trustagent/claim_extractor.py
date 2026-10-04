
"""TrustAgent Step 1 — splits a draft answer into verifiable claims."""

from ai_core.llm_gateway import call_llm

import json

import re





def extract_claims(draft_answer: str) -> list[str]:

    prompt = f"""List each individual factual/legal claim in the answer below as a JSON array of strings. Return ONLY the JSON array.



Answer: {draft_answer}



JSON array:"""

    raw = call_llm("groq/openai/gpt-oss-20b", prompt)

    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

    try:

        return json.loads(cleaned)

    except Exception:

        return [draft_answer]

