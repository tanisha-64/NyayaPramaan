"""
llm_gateway.py  (FULL REPLACEMENT)  ->  ai_core/llm_gateway.py

Same public API as before: call_llm(model, prompt) -> str.
Changes:
  * hard timeout + no litellm retries  -> a stuck provider no longer freezes the chat
  * iterative fallback (no recursion), no time.sleep(2)
  * thread-safe bounded cache (max 256) -> safe for the parallel post-steps
  * LLM_FAIL_TEXT constant + is_llm_failure() so callers can tell
    "all providers down" from a real answer (so it is never verified/saved as an answer)
  * models are env-configurable (providers retire models often)
"""
import hashlib
import os
import threading
from collections import OrderedDict

import litellm
from dotenv import load_dotenv

load_dotenv()
for _k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
    os.environ[_k] = os.getenv(_k, "")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/deepseek/deepseek-r1:free")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))

LLM_FAIL_TEXT = "I'm currently experiencing high demand across providers. Please try again in a moment."

FALLBACK_CHAIN = {
    "gemini": [GROQ_MODEL, OPENROUTER_MODEL],
    "groq": [GEMINI_MODEL, OPENROUTER_MODEL],
    "openrouter": [GROQ_MODEL, GEMINI_MODEL],
}

_CACHE_MAX = 256
_cache: "OrderedDict[str, str]" = OrderedDict()
_lock = threading.Lock()


def _provider(model: str) -> str:
    return model.split("/")[0]


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def is_llm_failure(text: str) -> bool:
    return (text or "").strip() == LLM_FAIL_TEXT


def call_llm(model: str, prompt: str, _tried=None) -> str:
    key = _cache_key(model, prompt)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    order = [model] + [m for m in FALLBACK_CHAIN.get(_provider(model), []) if m != model]
    for m in order:
        try:
            resp = litellm.completion(
                model=m,
                messages=[{"role": "user", "content": prompt}],
                timeout=LLM_TIMEOUT,
                num_retries=0,
            )
            result = resp["choices"][0]["message"]["content"] or ""
            if not result.strip():
                raise ValueError("empty completion")
            with _lock:
                _cache[key] = result
                while len(_cache) > _CACHE_MAX:
                    _cache.popitem(last=False)
            return result
        except Exception as e:  # noqa: BLE001
            print(f"[llm_gateway] {m} unavailable ({type(e).__name__}) -> next")
    return LLM_FAIL_TEXT