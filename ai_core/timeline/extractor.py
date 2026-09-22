"""
Case Timeline & Order-History Extractor (synopsis Section 4.2)
Text-only task -- routed through Groq to conserve Gemini's limited free quota.
"""
from ai_core.llm_gateway import call_llm

def extract_timeline(case_text: str) -> str:
    if not case_text or not case_text.strip():
        return "No explicit dates found."
    sample = case_text[:12000] if len(case_text) > 12000 else case_text
    prompt = f"""Extract every date and associated event/order from this case
file as a chronological bullet list in this exact format:
- [Date] -- [Event]

If no explicit dates are found, say "No explicit dates found."

CASE FILE:
{sample}"""
    return call_llm("groq/openai/gpt-oss-20b", prompt)