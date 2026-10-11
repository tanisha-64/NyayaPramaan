"""
Legal-scope guard. NyayaPramaan provides evidence-backed analysis; it must not predict or decide the outcome of a
case. Deterministic (regex) so it cannot be talked out of by the model.

* asks_for_outcome_prediction(query)  - the user asks who will win / what the court will decide (English / Hinglish)
* contains_outcome_prediction(answer) - the generated answer itself predicts or pronounces an outcome
* PREDICTION_PROMPT_RULE              - extra rule added to the answer prompt when a prediction was requested
* DISCLAIMER                          - appended to the response (as a separate field and to the text) when relevant
"""
import re

DISCLAIMER = ("NyayaPramaan does not predict or decide the outcome of a case. This analysis is limited to what the "
              "document and the cited law show; the final determination rests with the court and a qualified legal "
              "professional.")

PREDICTION_PROMPT_RULE = (
    "7. The user is asking about the likely OUTCOME. Do NOT predict, estimate odds, or say who will win/lose or what the "
    "court will decide. Instead set out (a) the facts and evidence in the document that favour each side, (b) the legal "
    "questions the evidence bears on, and (c) what is missing. State that the final determination belongs to the court "
    "and a qualified legal professional.\n"
)

_QUERY_PATTERNS = [
    r"\bwill (i|we|he|she|they|the (plaintiff|defendant|petitioner|respondent|accused|appellant|court|judge))\b.{0,40}\b(win|lose|succeed|be convicted|be acquitted|get|grant|dismiss|allow|decide|rule|hold)\b",
    r"\b(chances?|odds|probability|likelihood)\b.{0,30}\b(of|to)\b",
    r"\b(likely|going) to (win|lose|succeed|be convicted|be acquitted)\b",
    r"\bwho (will|would|is going to) win\b",
    r"\bwhat will the (court|judge|bench)\b.{0,20}\b(decide|hold|rule|do|say)\b",
    r"\bpredict\b.{0,30}\b(verdict|judgment|outcome|decision|result)\b",
    r"\b(verdict|judgment|decision|outcome)\b.{0,20}\b(kya|kaisa|kaisi)\b.{0,10}\b(hoga|aayega|ayega)\b",
    r"\b(jeet|jit)(enge|ega|egi|unga|ungi|na)\b",
    r"\bhar (jaunga|jaenge|jayega|jayegi)\b",
    r"\bkya (main|hum|woh|vo|plaintiff|defendant)\b.{0,25}\b(jeet|jit|har)\b",
    r"\bfaisla\b.{0,20}\bkya\b.{0,10}\bhoga\b",
]
_ANSWER_PATTERNS = [
    r"\b(will|is certain to|is sure to|is bound to|is likely to) (win|lose|succeed|be convicted|be acquitted|be dismissed|be allowed)\b",
    r"\bthe (court|judge|bench) (will|shall) (hold|decide|grant|dismiss|allow|rule|convict|acquit)\b",
    r"\b(you|the plaintiff|the defendant|the accused|the petitioner|the respondent) (will|would) (certainly|definitely|surely)?\s*(win|lose|be convicted|be acquitted)\b",
    r"\b(\d{1,3})\s?%\s+(chance|probability|likelihood)\b",
    r"\b(chances?|odds) (are|of)\b.{0,30}\b(high|low|good|poor|strong|slim|better)\b",
]
_Q = [re.compile(p, re.IGNORECASE) for p in _QUERY_PATTERNS]
_A = [re.compile(p, re.IGNORECASE) for p in _ANSWER_PATTERNS]


def asks_for_outcome_prediction(query: str) -> bool:
    text = query or ""
    return any(p.search(text) for p in _Q)


def contains_outcome_prediction(answer: str) -> bool:
    text = answer or ""
    return any(p.search(text) for p in _A)
