"""
Summarizer (synopsis Section 4.2)
Uses Groq (high free-tier limit) since summarization is a pure text-task
and does not require Gemini's specific multimodal capability.
"""
from ai_core.llm_gateway import call_llm

def summarize_case(case_text: str) -> str:
    if not case_text or not case_text.strip():
        return "No text content extracted to summarize."
    # For large judgments, combine head and tail (parties, facts, issues, and final ruling)
    if len(case_text) > 12000:
        sample = case_text[:8000] + "\n\n[...]\n\n" + case_text[-4000:]
    else:
        sample = case_text
    prompt = f"Summarize this legal case in 4-5 clear sentences highlighting key facts, legal provisions, and ruling:\n\n{sample}"
    return call_llm("groq/openai/gpt-oss-20b", prompt)