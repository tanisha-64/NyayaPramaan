
"""Timeline Extractor — chronological date/event extraction."""

from ai_core.llm_gateway import call_llm





def extract_timeline(case_text: str) -> str:

    prompt = f"""Extract every date and associated event/order from this case

file as a chronological bullet list in this exact format:

- [Date] -- [Event]



If no explicit dates are found, say "No explicit dates found."



CASE FILE:

{case_text}"""

    return call_llm("groq/openai/gpt-oss-20b", prompt)

