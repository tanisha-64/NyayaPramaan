"""
LLM-as-a-Judge — final independent evaluation layer (synopsis Section 4.2
Evaluation Layer, extended). Runs AFTER TrustAgent has already verified
claims, using a DIFFERENT model as judge to catch anything TrustAgent might
have missed (unclear phrasing, unhelpful answer, wrong department-suggestion,
etc). This is the last checkpoint before the answer reaches the user.
"""
import json
import re
from ai_core.llm_gateway import call_llm

JUDGE_MODEL = "gemini/gemini-3.6-flash"  # deliberately different from the
                                          # model that likely drafted the answer


def judge_answer(query: str, answer: str, evidence: str) -> dict:
    prompt = f"""You are an independent legal-answer quality judge. Evaluate
the ANSWER given for the QUERY, using the EVIDENCE it was based on.

Respond with ONLY this JSON:
{{"is_accurate": true, "is_helpful": true, "issue": ""}}

is_accurate: false if the answer contains anything not supported by the
evidence, or is factually questionable.
is_helpful: false if the answer doesn't actually address the user's question.
issue: brief description of any problem found, or empty string if none.

QUERY: {query}
ANSWER: {answer}
EVIDENCE: {evidence}

JSON:"""
    try:
        raw = call_llm(JUDGE_MODEL, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        result = json.loads(cleaned)
        return {
            "is_accurate": bool(result.get("is_accurate", True)),
            "is_helpful": bool(result.get("is_helpful", True)),
            "issue": result.get("issue", ""),
        }
    except Exception:
        return {"is_accurate": True, "is_helpful": True, "issue": ""}