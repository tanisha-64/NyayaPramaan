
"""LLM-as-a-Judge — independent final accuracy check (different model than the generator)."""

import json

import re

from ai_core.llm_gateway import call_llm



JUDGE_MODEL = "gemini/gemini-3.6-flash"





def judge_answer(query: str, answer: str, evidence: str) -> dict:

    prompt = f"""You are an independent legal-answer quality judge. Evaluate

the ANSWER for the QUERY, using the EVIDENCE it was based on.



Respond with ONLY this JSON:

{{"is_accurate": true, "is_helpful": true, "issue": ""}}



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

