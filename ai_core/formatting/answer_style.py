"""
answer_style.py  (NEW FILE)  ->  ai_core/formatting/answer_style.py

1) STYLE_GUIDE: put in every answer prompt so replies read like a helpful chat
   (one friendly lead sentence, then a few tidy lines) instead of choppy fragments.
2) tidy_answer(): cleans markdown leftovers so the existing AnswerCard
   (white-space: pre-wrap, no markdown renderer) shows a clean, readable text.
   Set PLAIN_TEXT_ANSWERS=0 on Render if you install react-markdown on the frontend.
"""
import os
import re

STYLE_GUIDE = (
    "ANSWER STYLE (follow strictly):\n"
    "- Open with ONE clear, friendly sentence that directly answers the question, like a knowledgeable "
    "friend explaining in chat. No headings for short answers.\n"
    "- Then, only if it helps, add 2-5 short lines. Each starts with a relevant emoji and a short label, "
    "e.g. '📌 Meaning: ...', '⚖️ Rule: ...', '📄 In the document: ... [Page 3]', '👉 Example: ...'.\n"
    "- Plain text only: no markdown asterisks, no # headings, no tables.\n"
    "- Do not repeat disclaimers, do not repeat the question, do not add an 'In Short' line "
    "(the app adds it separately).\n"
)


def tidy_answer(text: str) -> str:
    if os.getenv("PLAIN_TEXT_ANSWERS", "1") == "0" or not text:
        return text
    t = text.replace("\r\n", "\n")
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*(.+?)\s*#*\s*$", r"📌 \1", t)       # headings
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)                                   # bold
    t = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"\1", t)    # italics
    t = re.sub(r"(?m)^\s*[-*•]\s+", "• ", t)                                 # bullets
    t = re.sub(r"(?m)^\s*(\d+)[.)]\s+", r"\1. ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()