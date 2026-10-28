import pytest

from ai_core import llm_gateway as gw


def _ok(text):
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    gw._cache.clear(); gw._down_until.clear()
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "OPENROUTER_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "x"); monkeypatch.setenv("GROQ_API_KEY", "y")


def test_falls_back_to_next_provider_and_pauses_the_failed_one(monkeypatch):
    calls = []

    def fake(model, **k):
        calls.append(model)
        if model.startswith("gemini"):
            raise RuntimeError("503")
        return _ok("groq answer")

    monkeypatch.setattr(gw.litellm, "completion", fake)
    assert gw.call_llm("gemini/x", "q1") == "groq answer"
    assert calls[0].startswith("gemini") and calls[1].startswith("groq")
    calls.clear()
    assert gw.call_llm("gemini/x", "q2") == "groq answer"      # gemini paused for 60s -> not tried again
    assert len(calls) == 1 and calls[0].startswith("groq")


def test_all_providers_fail_returns_marker_text(monkeypatch):
    monkeypatch.setattr(gw.litellm, "completion", lambda model, **k: (_ for _ in ()).throw(RuntimeError("down")))
    out = gw.call_llm("groq/x", "q")
    assert gw.is_llm_failure(out) and out == gw.LLM_FAIL_TEXT


def test_providers_without_keys_are_skipped(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    seen = []
    monkeypatch.setattr(gw.litellm, "completion", lambda model, **k: seen.append(model) or _ok("ok"))
    gw.call_llm("gemini/x", "q")
    assert seen and all(not m.startswith("gemini") for m in seen)


def test_openrouter_needs_model_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "z")
    assert "openrouter" not in [p[0] for p in gw._order("openrouter")]


def test_result_is_cached(monkeypatch):
    n = {"c": 0}
    monkeypatch.setattr(gw.litellm, "completion", lambda model, **k: n.__setitem__("c", n["c"] + 1) or _ok("a"))
    gw.call_llm("groq/x", "same"); gw.call_llm("groq/x", "same")
    assert n["c"] == 1


def test_empty_completion_counts_as_failure(monkeypatch):
    monkeypatch.setattr(gw.litellm, "completion", lambda model, **k: _ok("   "))
    assert gw.is_llm_failure(gw.call_llm("groq/x", "q"))