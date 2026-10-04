
"""Adaptive Agent Router — cost-appropriate model selection."""



SIMPLE_MODEL = "groq/openai/gpt-oss-20b"

COMPLEX_MODEL = "gemini/gemini-3.6-flash"

COMPLEX_SIGNALS = ["precedent", "compare", "analyze", "timeline", "section", "jurisdiction"]





def choose_model(query: str) -> str:

    word_count = len(query.split())

    if word_count > 25 or any(w in query.lower() for w in COMPLEX_SIGNALS):

        return COMPLEX_MODEL

    return SIMPLE_MODEL

