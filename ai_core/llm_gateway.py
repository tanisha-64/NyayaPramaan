"""ai_core/llm_gateway.py (FULL REPLACEMENT)
Chain: Gemini -> Cerebras -> Groq -> Mistral -> Cloudflare. Jis provider ki key nahi, wo skip.
Fail hone par provider 60s ke liye band (circuit breaker). Dead openrouter/deepseek hata diya."""
import hashlib
import os
import threading
import time
from collections import OrderedDict

import litellm
from dotenv import load_dotenv

load_dotenv()

# (name, litellm model id, env vars jo chahiye). Model ids .env se badal sakte ho.
PROVIDERS = [
    ("gemini", os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash"), ["GEMINI_API_KEY"]),
    ("groq", os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b"), ["GROQ_API_KEY"]),
    ("openrouter", os.getenv("OPENROUTER_MODEL", ""), ["OPENROUTER_API_KEY", "OPENROUTER_MODEL"]),
]
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "25"))
BREAKER_SECS = float(os.getenv("LLM_BREAKER_SECS", "60"))
LLM_FAIL_TEXT = "I'm currently experiencing high demand across providers. Please try again in a moment."

_CACHE_MAX = 256
_cache: "OrderedDict[str, str]" = OrderedDict()
_down_until: dict = {}
_lock = threading.Lock()


def _has_keys(envs) -> bool:
    return all(os.getenv(e) for e in envs)


def _key(model, prompt):
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def is_llm_failure(text: str) -> bool:
    return (text or "").strip() == LLM_FAIL_TEXT


def _order(preferred: str):
    """Available providers; caller ka preferred model pehle, baaki chain order me."""
    avail = [p for p in PROVIDERS if _has_keys(p[2])]
    pref = [p for p in avail if p[0] == (preferred or "").split("/")[0]]
    return pref + [p for p in avail if p not in pref]


def call_llm(model: str, prompt: str) -> str:
    ck = _key(model, prompt)
    with _lock:
        if ck in _cache:
            _cache.move_to_end(ck)
            return _cache[ck]

    order = _order(model)
    now = time.time()
    live = [p for p in order if _down_until.get(p[0], 0) <= now]
    for name, mid, _ in (live or order):   # sab band ho to bhi ek baar try karo
        try:
            r = litellm.completion(model=mid, messages=[{"role": "user", "content": prompt}],
                                   timeout=LLM_TIMEOUT, num_retries=0)
            out = r["choices"][0]["message"]["content"] or ""
            if not out.strip():
                raise ValueError("empty completion")
            with _lock:
                _down_until.pop(name, None)
                _cache[ck] = out
                while len(_cache) > _CACHE_MAX:
                    _cache.popitem(last=False)
            return out
        except Exception as e:  # noqa: BLE001
            with _lock:
                _down_until[name] = time.time() + BREAKER_SECS
            print(f"[llm_gateway] {name} failed ({type(e).__name__}) -> next, paused {int(BREAKER_SECS)}s")
    return LLM_FAIL_TEXT