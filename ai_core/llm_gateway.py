"""
LLM Gateway — 3-tier automatic fallback (Gemini -> Groq -> OpenRouter) with lightweight response caching.

Cost / latency guards (all env-configurable, all bounded):
  LLM_TIMEOUT_SECONDS      per provider call (default 60); a stalled provider falls through to the next tier
  LLM_MAX_OUTPUT_TOKENS    output cap per call (default 8192; the quiz / game generators share this gateway and need little)
The fallback chain visits each model at most once per request (the `_tried` set), so a request makes a bounded number
of provider calls.
"""
import hashlib
import os
import time

import litellm
from dotenv import load_dotenv

load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")

_cache: dict[str, str] = {}
_CACHE_MAX_ENTRIES = 512

LLM_UNAVAILABLE_MESSAGE = "I'm currently experiencing high demand across providers. Please try again in a moment."

FALLBACK_CHAIN = {
    "gemini": ["groq/openai/gpt-oss-20b", "openrouter/deepseek/deepseek-r1:free"],
    "groq": ["gemini/gemini-3.6-flash", "openrouter/deepseek/deepseek-r1:free"],
    "openrouter": ["gemini/gemini-3.6-flash", "groq/openai/gpt-oss-20b"],
}


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except ValueError:
        return default


def _provider(model: str) -> str:
    return model.split("/")[0]


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def call_llm(model: str, prompt: str, _tried: set | None = None) -> str:
    key = _cache_key(model, prompt)
    if key in _cache:
        return _cache[key]

    _tried = _tried or set()
    _tried.add(model)

    try:
        response = litellm.completion(
            model=model, messages=[{"role": "user", "content": prompt}],
            timeout=_int_env("LLM_TIMEOUT_SECONDS", 60), max_tokens=_int_env("LLM_MAX_OUTPUT_TOKENS", 8192),
        )
        result = response["choices"][0]["message"]["content"]
        if not result or not str(result).strip():
            raise ValueError("empty completion")      # an empty reply is a failure: try the next tier

        if len(_cache) >= _CACHE_MAX_ENTRIES:
            _cache.pop(next(iter(_cache)))      # bounded: oldest entry out
        _cache[key] = result

        return result

    except Exception:
        provider = _provider(model)

        for fallback_model in FALLBACK_CHAIN.get(provider, []):
            if fallback_model not in _tried:
                print(f"[llm_gateway] {model} unavailable -> trying {fallback_model}")
                return call_llm(fallback_model, prompt, _tried)

        time.sleep(2)
        return LLM_UNAVAILABLE_MESSAGE
