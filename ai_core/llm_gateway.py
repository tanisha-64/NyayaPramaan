
"""

LLM Gateway — 3-tier automatic fallback (Gemini -> Groq -> OpenRouter) with

lightweight response caching.

"""

import litellm

import os

import time

import hashlib

from dotenv import load_dotenv



load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")



_cache: dict[str, str] = {}



FALLBACK_CHAIN = {

    "gemini": ["groq/openai/gpt-oss-20b", "openrouter/deepseek/deepseek-r1:free"],

    "groq": ["gemini/gemini-3.6-flash", "openrouter/deepseek/deepseek-r1:free"],

    "openrouter": ["gemini/gemini-3.6-flash", "groq/openai/gpt-oss-20b"],

}





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

        response = litellm.completion(model=model, messages=[{"role": "user", "content": prompt}])

        result = response["choices"][0]["message"]["content"]

        _cache[key] = result

        return result

    except Exception:

        provider = _provider(model)

        for fallback_model in FALLBACK_CHAIN.get(provider, []):

            if fallback_model not in _tried:

                print(f"[llm_gateway] {model} unavailable -> trying {fallback_model}")

                return call_llm(fallback_model, prompt, _tried)

        time.sleep(2)

        return "I'm currently experiencing high demand across providers. Please try again in a moment."

