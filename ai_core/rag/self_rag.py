
"""

Self-RAG — model self-critiques its own answer: usefulness-rating + TL;DR conclusion.

"""

import json

import re

from ai_core.llm_gateway import call_llm



REFLECTION_MODEL = "gemini/gemini-3.6-flash"





def self_reflect(query: str, answer: str, evidence: str) -> dict:

    prompt = f"""You just generated this ANSWER using the given EVIDENCE for

the QUERY. Respond with ONLY this JSON:

{{"usefulness": "high", "conclusion": "one clear sentence"}}



usefulness: "high"/"medium"/"low" based on how sufficient the evidence was.

conclusion: ONE short, direct sentence answering the user's core question (a TL;DR).



QUERY: {query}

ANSWER: {answer}

EVIDENCE: {evidence}



JSON:"""

    try:

        raw = call_llm(REFLECTION_MODEL, prompt)

        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

        result = json.loads(cleaned)

        usefulness = result.get("usefulness", "medium")

        if usefulness not in ("high", "medium", "low"):

            usefulness = "medium"

        return {"usefulness": usefulness, "conclusion": result.get("conclusion", "")}

    except Exception:

        return {"usefulness": "medium", "conclusion": ""}

