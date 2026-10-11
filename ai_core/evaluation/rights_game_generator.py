"""
Rights-Rakshak Game — generates realistic, everyday scenarios where the
user picks how to respond. Choices are shuffled after generation so the
correct answer isn't predictably always in the same position.
Includes a rich curated scenario bank so the game loads instantly without delay.
"""
import json
import re
import random
from ai_core.llm_gateway import call_llm
from ai_core.evaluation.llm_judge import judge_answer

CATEGORIES = ["arrest_rights", "consumer_rights", "property_rights", "workplace_rights", "women_safety_rights"]

CURATED_SCENARIOS = [
    {
        "category": "arrest_rights",
        "title": "Police Detention Without Grounds",
        "scenario_text": "You are stopped by police at 9:00 PM near a metro station. An officer demands you accompany them to the police station without stating any reason or showing identification.",
        "choices": [
            {
                "text": "Politely ask for the officer's name/designation and demand to know the specific grounds of arrest under Section 50 CrPC / Section 47 BNSS.",
                "is_best": True,
                "points": 10,
                "explanation": "Under Article 22(1) of the Constitution and Section 50 CrPC (Section 47 BNSS), every person has the fundamental right to be informed of the grounds of arrest and the right to consult a legal practitioner of their choice."
            },
            {
                "text": "Physically resist the officer and try to run away.",
                "is_best": False,
                "points": 0,
                "explanation": "Physically resisting or fleeing from a public servant discharging duties can lead to additional criminal charges under Section 186/353 IPC (Section 221/132 BNS)."
            },
            {
                "text": "Offer money on the spot to settle the matter immediately.",
                "is_best": False,
                "points": 0,
                "explanation": "Attempting to bribe a police officer is a cognizable offence under the Prevention of Corruption Act."
            }
        ],
        "verified": True
    },
    {
        "category": "arrest_rights",
        "title": "Arrest of a Woman After Sunset",
        "scenario_text": "At 8:30 PM, police officers arrive at a woman's residence intending to arrest her in connection with a non-violent cheating case.",
        "choices": [
            {
                "text": "State that under Section 46(4) CrPC / Section 43(5) BNSS, a woman cannot be arrested after sunset and before sunrise except in exceptional circumstances with prior Magistrate permission.",
                "is_best": True,
                "points": 10,
                "explanation": "Section 46(4) of CrPC strictly prohibits arresting women between sunset and sunrise except in exceptional circumstances where a female police officer obtains prior written permission from the Judicial Magistrate."
            },
            {
                "text": "Go to the station immediately with the male officers without asking any questions.",
                "is_best": False,
                "points": 2,
                "explanation": "A woman is entitled to be accompanied by a female officer and cannot be taken into custody at night without judicial sanction."
            },
            {
                "text": "Lock the door and refuse to ever speak to the legal authorities.",
                "is_best": False,
                "points": 0,
                "explanation": "Refusing communication entirely obstructs lawful inquiry; exercising statutory procedural protections is the lawful course."
            }
        ],
        "verified": True
    },
    {
        "category": "consumer_rights",
        "title": "Defective Laptop & Refund Refusal",
        "scenario_text": "You purchased a new laptop that developed a motherboard defect within 7 days. The authorized service center refuses repair or replacement, claiming 'no refund/return policy'.",
        "choices": [
            {
                "text": "File a formal complaint on the National Consumer Helpline (NCH / INGRAM) or file a claim before the District Consumer Commission under the Consumer Protection Act, 2019.",
                "is_best": True,
                "points": 10,
                "explanation": "Under the Consumer Protection Act 2019, 'no refund/replacement' clauses for defective goods constitute an Unfair Trade Practice. Consumers have the right to seek replacement, repair, or full refund with compensation."
            },
            {
                "text": "Accept the loss and buy another laptop from the same manufacturer.",
                "is_best": False,
                "points": 0,
                "explanation": "Consumers are legally protected against product defects and unfair trade practices."
            },
            {
                "text": "Threaten the store staff on social media with abusive language.",
                "is_best": False,
                "points": 0,
                "explanation": "Defamation and intimidation can expose you to civil and criminal liability; legal consumer forums are the appropriate remedy."
            }
        ],
        "verified": True
    },
    {
        "category": "property_rights",
        "title": "Tenant Eviction Without Due Process",
        "scenario_text": "Your landlord abruptly cuts off water and electricity to your rented apartment and gives you 24 hours to vacate without a court order or written notice.",
        "choices": [
            {
                "text": "Approach the Rent Controller / Civil Court for restoration of essential amenities and an injunction against illegal dispossession.",
                "is_best": True,
                "points": 10,
                "explanation": "Under state Rent Control Acts and standard tenancy laws, a landlord cannot disconnect essential services or forcibly evict a tenant without following due process of law."
            },
            {
                "text": "Stop paying rent forever while continuing to reside there indefinitely.",
                "is_best": False,
                "points": 2,
                "explanation": "Defaulting on rent makes you a tenant-in-default and weakens your legal defense against eviction."
            },
            {
                "text": "Vandalize the property before leaving.",
                "is_best": False,
                "points": 0,
                "explanation": "Vandalism and mischief are punishable criminal offences under Section 425 IPC / Section 324 BNS."
            }
        ],
        "verified": True
    },
    {
        "category": "workplace_rights",
        "title": "Unpaid Salary and Hostile Termination",
        "scenario_text": "An employer terminates an employee without the mandatory notice period or severance pay and refuses to release the last two months of salary.",
        "choices": [
            {
                "text": "Send a formal legal notice through an advocate and file a complaint before the Labour Commissioner / Industrial Tribunal or under the Shops and Establishments Act.",
                "is_best": True,
                "points": 10,
                "explanation": "Employees are protected under the Payment of Wages Act, Industrial Disputes Act, and state Shops & Establishments Acts against wrongful withholding of earned wages."
            },
            {
                "text": "Post company trade secrets online as revenge.",
                "is_best": False,
                "points": 0,
                "explanation": "Breach of NDA and leaking proprietary data violates the IT Act and civil trade secret laws."
            },
            {
                "text": "Ignore the pending salary and quietly walk away.",
                "is_best": False,
                "points": 2,
                "explanation": "Earned wages are statutory property; employees have enforceable recovery rights."
            }
        ],
        "verified": True
    },
    {
        "category": "women_safety_rights",
        "title": "Workplace Harassment & POSH Committee",
        "scenario_text": "A female employee experiences persistent unwelcome sexual remarks from a senior colleague. The HR manager tells her to 'let it go' and refuses to act.",
        "choices": [
            {
                "text": "Submit a formal written complaint to the Internal Complaints Committee (ICC) mandated under the POSH Act, 2013, or approach the Local Complaints Committee (LCC).",
                "is_best": True,
                "points": 10,
                "explanation": "The Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 mandates an impartial ICC inquiry within 90 days with strict confidentiality."
            },
            {
                "text": "Immediately resign and remain silent about the misconduct.",
                "is_best": False,
                "points": 2,
                "explanation": "The POSH Act protects employees against victimization and guarantees a safe work environment."
            },
            {
                "text": "Confront the harasser physically in the office lobby.",
                "is_best": False,
                "points": 0,
                "explanation": "Physical confrontation can complicate the legal complaint; structured ICC proceedings ensure legal remedy and accountability."
            }
        ],
        "verified": True
    }
]


def _shuffle_scenario(s: dict) -> dict:
    choices = [dict(c) for c in s.get("choices", [])]
    random.shuffle(choices)
    return {
        "id": s.get("id", f"sc_{random.randint(1000, 9999)}"),
        "title": s.get("title", "Legal Dilemma"),
        "scenario_text": s.get("scenario_text", ""),
        "choices": choices,
        "category": s.get("category", "general_rights"),
        "verified": s.get("verified", True)
    }


def generate_scenario(category: str) -> dict:
    # Check if we have curated scenarios matching the category
    matching = [s for s in CURATED_SCENARIOS if s.get("category") == category]
    if not matching:
        matching = CURATED_SCENARIOS

    prompt = f"""Create a realistic, everyday Indian scenario about "{category}"
where a person must choose how to respond, and learns their actual legal
rights. Respond with ONLY this JSON:

{{"title": "short catchy title", "scenario_text": "2-3 sentence situation ending in a decision point",
"choices": [
  {{"text": "Option A", "is_best": true, "points": 10, "explanation": "why this is legally correct"}},
  {{"text": "Option B", "is_best": false, "points": 2, "explanation": "why this is legally weaker"}},
  {{"text": "Option C", "is_best": false, "points": 0, "explanation": "why this is legally wrong"}}
]}}

Be accurate about Indian law (Constitution, BNS/CrPC/BNSS, Consumer Protection Act, etc).

JSON:"""
    try:
        raw = call_llm("gemini/gemini-2.0-flash", prompt)
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
        scenario = json.loads(cleaned)
        scenario["category"] = category

        # shuffle choice-order so the correct answer isn't always in the same position
        random.shuffle(scenario["choices"])

        best_choice = next((c for c in scenario["choices"] if c["is_best"]), None)
        if best_choice:
            judgment = judge_answer(scenario["scenario_text"], best_choice["explanation"], f"Indian law on {category}")
            scenario["verified"] = judgment["is_accurate"]
        return scenario
    except Exception as e:
        print(f"[rights_game_generator] LLM generation fallback: {e}")
        return _shuffle_scenario(random.choice(matching))
