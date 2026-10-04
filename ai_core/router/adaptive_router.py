"""
Adaptive Agent Router (synopsis Section 4.2)
Chooses the most capable model based on query complexity.
Simple queries -> Groq (fast/free). Complex reasoning -> Gemini 3.8 / 3.7 Flash.
"""

SIMPLE_MODEL = "groq/openai/gpt-oss-20b"
COMPLEX_MODEL = "gemini/gemini-3.8-flash"

COMPLEX_SIGNALS = ["precedent", "compare", "analyze", "timeline", "section", "jurisdiction", "judgment", "ratio", "constitutional"]

def choose_model(query: str) -> str:
    word_count = len(query.split())
    if word_count > 25 or any(w in query.lower() for w in COMPLEX_SIGNALS):
        return COMPLEX_MODEL
    return SIMPLE_MODEL