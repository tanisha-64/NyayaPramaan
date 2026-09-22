"""
Self-RAG Layer — the model critiques its OWN answer before finalizing:
checks if the retrieved evidence was actually sufficient/relevant, and
produces a short conclusive summary + a usefulness rating. Combined with
CRAG (external correction) and TrustAgent (claim verification), this
closes the loop for a hallucination-resistant pipeline:
  RAG (retrieve) -> CRAG (correct if retrieval weak) ->
  TrustAgent (verify claims) -> Self-RAG (self-critique + conclude)
"""
import json
import re
from ai_core.llm_gateway import call_llm

REFLECTION_MODEL = "gemini/gemini-3.6-flash"


def self_reflect(query: str, answer: str, evidence: str) -> dict:
    prompt = f"""You just generated this ANSWER using the given EVIDENCE for
the QUERY. Critically self-assess it. Respond with ONLY this JSON:

{{"usefulness": "high", "conclusion": "one clear sentence"}}

usefulness: "high" if the evidence was clearly sufficient and the answer
fully resolves the query; "medium" if partially sufficient; "low" if the
evidence was weak/tangential to the query.

conclusion: ONE short, direct sentence that answers the user's core
question in plain language (a TL;DR) -- even if the fuller answer above
has more nuance.

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