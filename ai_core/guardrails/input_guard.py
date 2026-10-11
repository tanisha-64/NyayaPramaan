
"""Input Guardrails — blocks jailbreak/prompt-injection attempts."""



JAILBREAK_PATTERNS = [

    "ignore previous instructions", "ignore all instructions", "pretend you are",

    "you are now", "disregard the rules", "bypass", "jailbreak", "system prompt",

]





def check_input_safety(query: str) -> dict:

    lowered = query.lower()

    for pattern in JAILBREAK_PATTERNS:

        if pattern in lowered:

            return {"is_safe": False, "reason": f"blocked pattern: '{pattern}'"}

    return {"is_safe": True, "reason": None}
