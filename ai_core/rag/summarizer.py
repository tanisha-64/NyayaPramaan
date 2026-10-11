
"""Summarizer — Groq (high free-tier limit) for pure text summarization."""

from ai_core.llm_gateway import call_llm





def summarize_case(case_text: str) -> str:

    prompt = f"Summarize this legal case in 4-5 clear sentences:\n\n{case_text}"

    return call_llm("groq/openai/gpt-oss-20b", prompt)

