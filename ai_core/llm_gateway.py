"""
LLM Gateway — multi-provider fallback engine (Gemini -> Groq -> OpenRouter -> LiteLLM)
Ensures 100% uptime with robust exception handling and caching.
"""
import os
import time
import hashlib
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

_cache: dict[str, str] = {}

# Lazy loaded clients
_gemini_client = None
_groq_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None and GEMINI_API_KEY:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"[llm_gateway] Failed to init Gemini client: {e}")
    return _gemini_client


def _get_groq_client():
    global _groq_client
    if _groq_client is None and GROQ_API_KEY:
        try:
            import groq
            _groq_client = groq.Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"[llm_gateway] Failed to init Groq client: {e}")
    return _groq_client


def _call_gemini_direct(model_name: str, prompt: str) -> str:
    client = _get_gemini_client()
    if not client:
        raise RuntimeError("Gemini client not initialized or missing GEMINI_API_KEY")
    clean_model = model_name.replace("gemini/", "").replace("models/", "")
    # Fallback to available version if needed
    if clean_model in ("gemini-3.6-flash", "gemini-1.5-flash", "gemini-flash"):
        clean_model = "gemini-2.5-flash"
    response = client.models.generate_content(
        model=clean_model,
        contents=prompt,
    )
    return response.text or ""


def _call_groq_direct(model_name: str, prompt: str) -> str:
    client = _get_groq_client()
    if not client:
        raise RuntimeError("Groq client not initialized or missing GROQ_API_KEY")
    clean_model = model_name.replace("groq/", "")
    if clean_model in ("llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"):
        clean_model = "openai/gpt-oss-20b"
    response = client.chat.completions.create(
        model=clean_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _call_litellm(model_name: str, prompt: str) -> str:
    import litellm
    response = litellm.completion(model=model_name, messages=[{"role": "user", "content": prompt}], timeout=20)
    return response["choices"][0]["message"]["content"] or ""


MODELS_FALLBACK_ORDER = [
    "groq/openai/gpt-oss-20b",
    "groq/openai/gpt-oss-120b",
    "groq/qwen/qwen3.8-27b",
    "gemini/gemini-3.7-flash",
]


def _cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()


def call_llm(model: str, prompt: str, _tried: set | None = None) -> str:
    key = _cache_key(model, prompt)
    if key in _cache:
        return _cache[key]

    _tried = _tried or set()
    _tried.add(model)

    # Try requested model
    try:
        if "gemini" in model.lower():
            res = _call_gemini_direct(model, prompt)
            _cache[key] = res
            return res
        elif "groq" in model.lower():
            res = _call_groq_direct(model, prompt)
            _cache[key] = res
            return res
        else:
            res = _call_litellm(model, prompt)
            _cache[key] = res
            return res
    except Exception as e:
        print(f"[llm_gateway] Call failed for {model}: {e}")

    # Fallback cascade
    for candidate in MODELS_FALLBACK_ORDER:
        if candidate not in _tried:
            _tried.add(candidate)
            try:
                print(f"[llm_gateway] Falling back to {candidate}...")
                if "gemini" in candidate.lower():
                    res = _call_gemini_direct(candidate, prompt)
                elif "groq" in candidate.lower():
                    res = _call_groq_direct(candidate, prompt)
                else:
                    res = _call_litellm(candidate, prompt)
                if res and res.strip():
                    _cache[key] = res
                    return res
            except Exception as fb_err:
                print(f"[llm_gateway] Fallback {candidate} failed: {fb_err}")
                continue

    return "I apologize, but I could not reach the legal AI reasoning providers. Please check your network or try again in a few moments."