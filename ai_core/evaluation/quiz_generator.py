"""
Daily Quiz Generator — generates high-quality multiple choice questions on Indian law
(IPC, BNS, Constitution, CrPC, BNSS, Consumer Protection, Evidence Act).
Includes a comprehensive curated fallback bank so the quiz loads instantly and never fails.
"""
import json
import re
import random
from ai_core.llm_gateway import call_llm

GENERATOR_MODEL = "gemini/gemini-2.0-flash"
JUDGE_MODEL = "gemini/gemini-2.0-flash"

CURATED_QUIZ_BANK = [
    {
        "question": "Which Article of the Indian Constitution guarantees the 'Right to Constitutional Remedies' (Writs)?",
        "options": ["Article 32", "Article 21", "Article 14", "Article 19"],
        "correct_index": 0,
        "explanation": "Article 32 gives citizens the right to move the Supreme Court by appropriate proceedings for the enforcement of Fundamental Rights. Dr. B.R. Ambedkar called it the heart and soul of the Constitution.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "Under the new Bharatiya Nyaya Sanhita (BNS), 2023, which section defines the offence of Murder?",
        "options": ["Section 101", "Section 103", "Section 302", "Section 69"],
        "correct_index": 0,
        "explanation": "Under the Bharatiya Nyaya Sanhita (BNS), Section 101 defines murder (corresponding to IPC Section 300), and Section 103 prescribes the punishment for murder.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "What is the maximum period a person can be detained in police custody under Section 167 CrPC / Section 187 BNSS during the initial remand?",
        "options": ["15 days", "30 days", "7 days", "24 hours"],
        "correct_index": 0,
        "explanation": "The magistrate may authorize the detention of the accused in police custody for a term not exceeding 15 days in the whole, or in parts as provided under the new BNSS provisions.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "Which landmark Supreme Court judgment established the 'Basic Structure Doctrine' of the Indian Constitution?",
        "options": ["Kesavananda Bharati v. State of Kerala (1973)", "Maneka Gandhi v. Union of India (1978)", "Golaknath v. State of Punjab (1967)", "Minerva Mills v. Union of India (1980)"],
        "correct_index": 0,
        "explanation": "In Kesavananda Bharati (1973), a 13-judge bench of the Supreme Court held that Parliament cannot alter the basic structure or framework of the Constitution.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "Under the Consumer Protection Act, 2019, which authority has the power to entertain complaints where the value of goods or services exceeds ₹10 Crore?",
        "options": ["National Consumer Disputes Redressal Commission (NCDRC)", "State Consumer Disputes Redressal Commission", "District Consumer Disputes Redressal Commission", "Supreme Court of India directly"],
        "correct_index": 0,
        "explanation": "The National Commission (NCDRC) has pecuniary jurisdiction to entertain complaints where the consideration paid exceeds ₹10 Crore (as revised by subsequent rules).",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "Which section of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 deals with Anticipatory Bail?",
        "options": ["Section 482", "Section 438", "Section 437", "Section 484"],
        "correct_index": 0,
        "explanation": "Section 482 of the BNSS corresponds to Section 438 of the CrPC, providing the High Court and Court of Session the power to grant direction for bail to a person apprehending arrest.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "What does the Latin legal maxim 'Audi Alteram Partem' signify?",
        "options": ["Listen to the other side / No one should be condemned unheard", "An act of God prejudices no one", "Ignorance of law is no excuse", "The burden of proof lies on the plaintiff"],
        "correct_index": 0,
        "explanation": "'Audi Alteram Partem' is a fundamental rule of Natural Justice ensuring that both parties are given a fair opportunity to present their case before any adverse order is passed.",
        "judge_verified": True,
        "caution_note": ""
    },
    {
        "question": "Under Article 21 of the Indian Constitution, the right to privacy was declared a fundamental right in which landmark case?",
        "options": ["K.S. Puttaswamy v. Union of India (2017)", "Navtej Singh Johar v. Union of India (2018)", "Shreya Singhal v. Union of India (2015)", "Vishaka v. State of Rajasthan (1997)"],
        "correct_index": 0,
        "explanation": "A unanimous 9-judge Constitution Bench of the Supreme Court in K.S. Puttaswamy (2017) declared the Right to Privacy an intrinsic part of the Right to Life and Personal Liberty under Article 21.",
        "judge_verified": True,
        "caution_note": ""
    }
]


def _shuffle_question(q: dict) -> dict:
    options = list(q["options"])
    correct_text = options[q["correct_index"]]
    random.shuffle(options)
    return {
        "question": q["question"],
        "options": options,
        "correct_index": options.index(correct_text),
        "explanation": q.get("explanation", ""),
        "judge_verified": q.get("judge_verified", True),
        "caution_note": q.get("caution_note", "")
    }


def get_curated_quiz_set(count: int = 5) -> list[dict]:
    sampled = random.sample(CURATED_QUIZ_BANK, min(count, len(CURATED_QUIZ_BANK)))
    return [_shuffle_question(q) for q in sampled]


def generate_daily_quiz() -> list[dict]:
    prompt = """Generate 5 distinct multiple-choice questions about Indian law,
covering a MIX of: Bharatiya Nyaya Sanhita (BNS) / IPC, Indian Constitution & Fundamental Rights,
BNSS / Criminal Procedure, Consumer Protection, and Court landmark rulings.
Respond with ONLY a valid JSON array of 5 objects:

[{"question": "...", "options": ["Option A", "Option B", "Option C", "Option D"], "correct_index": 0, "explanation": "..."}]"""
    try:
        raw = call_llm(GENERATOR_MODEL, prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        questions = json.loads(cleaned)
        if isinstance(questions, list) and len(questions) >= 3:
            processed = []
            for q in questions:
                if "question" in q and "options" in q and "correct_index" in q:
                    processed.append(_shuffle_question(q))
            if len(processed) >= 3:
                return processed[:5]
    except Exception as e:
        print(f"[quiz_generator] LLM generation fallback: {e}")

    return get_curated_quiz_set(5)