"""
Self-RAG — self-critique layer. Now also decides whether a conclusion
box genuinely adds value (skips it for already-short/direct answers to
avoid redundant "In Short" on every single response).
"""
import json
import re
from ai_core.llm_gateway import call_llm

REFLECTION_MODEL = "gemini/gemini-3.6-flash"


def self_reflect(query: str, answer: str, evidence: str) -> dict:
    prompt = f"""You just generated this ANSWER using the given EVIDENCE for
the QUERY. Respond with ONLY this JSON:
{{"usefulness": "high", "conclusion": "one clear sentence", "conclusion_needed": true}}

usefulness: "high"/"medium"/"low" based on how sufficient the evidence was.
conclusion: ONE short, direct sentence answering the user's core question.
conclusion_needed: false if the ANSWER itself is ALREADY short and direct
(e.g. under 3 sentences, no tables/lists) such that a separate "In Short"
box would just repeat it -- true otherwise (e.g. when the answer is a
table, a multi-paragraph explanation, or a list).

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
        return {
            "usefulness": usefulness,
            "conclusion": result.get("conclusion", ""),
            "conclusion_needed": bool(result.get("conclusion_needed", True)),
        }
    except Exception:
        return {"usefulness": "medium", "conclusion": "", "conclusion_needed": False}
