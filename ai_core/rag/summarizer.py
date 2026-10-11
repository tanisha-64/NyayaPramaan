"""Summarizer — Groq (high free-tier limit) for pure text summarization."""

from ai_core.guardrails.output_guard import redact_pii
from ai_core.llm_gateway import call_llm

MAX_HEAD_CHARS = 12000      # a judgment's caption, facts and issues are at the start
MAX_TAIL_CHARS = 5000       # the operative order is at the end


def prepare_text_for_llm(case_text: str) -> str:
    """Bounded, identifier-redacted text for an external LLM call. The full original stays in the database."""
    text = (case_text or "").replace("\f", "\n")
    if len(text) > MAX_HEAD_CHARS + MAX_TAIL_CHARS:
        text = f"{text[:MAX_HEAD_CHARS]}\n\n[... middle of the document omitted ...]\n\n{text[-MAX_TAIL_CHARS:]}"
    return redact_pii(text)


def summarize_case(case_text: str) -> str:
    prompt = ("Summarize this legal case in 4-5 clear sentences. Use only what the text says; do not add facts, "
              f"names, dates or sections that it does not contain:\n\n{prepare_text_for_llm(case_text)}")
    return call_llm("groq/openai/gpt-oss-20b", prompt)
