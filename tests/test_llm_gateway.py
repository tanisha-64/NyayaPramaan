import logging
import uuid
from unittest.mock import patch

from ai_core import llm_gateway


class ServiceUnavailableError(Exception):
    status_code = 503


def test_call_llm_logs_failure_category_and_uses_fallback(caplog):
    prompt = f"test prompt {uuid.uuid4()}"
    response = {"choices": [{"message": {"content": "fallback response"}}]}

    with patch.dict(llm_gateway.FALLBACK_CHAIN, {"test": ["groq/test-model"], "groq": []}), \
         patch.object(llm_gateway.litellm, "completion", side_effect=[RuntimeError("provider detail"), response]), \
         caplog.at_level(logging.WARNING, logger=llm_gateway.__name__):
        result = llm_gateway.call_llm("test/model", prompt)

    assert result == "fallback response"
    assert "RuntimeError" in caplog.text
    assert "provider detail" not in caplog.text


def test_call_llm_retries_gemini_503_then_uses_groq():
    prompt = f"retry prompt {uuid.uuid4()}"
    response = {"choices": [{"message": {"content": "groq response"}}]}

    with patch.object(
        llm_gateway.litellm,
        "completion",
        side_effect=[ServiceUnavailableError(), ServiceUnavailableError(), response],
    ) as completion, \
         patch.object(llm_gateway.time, "sleep"):
        result = llm_gateway.call_llm("gemini/test-model", prompt)

    assert result == "groq response"
    assert completion.call_count == 3
    assert all(call.kwargs["timeout"] == llm_gateway.LLM_TIMEOUT_SECONDS for call in completion.call_args_list)
    assert completion.call_args_list[0].kwargs["model"] == "gemini/test-model"
    assert completion.call_args_list[1].kwargs["model"] == "gemini/test-model"
    assert completion.call_args_list[2].kwargs["model"] == "groq/openai/gpt-oss-20b"


def test_call_llm_raises_clear_error_when_providers_fail():
    with patch.dict(llm_gateway.FALLBACK_CHAIN, {"gemini": ["groq/test-model"], "groq": []}), \
         patch.object(llm_gateway.litellm, "completion", side_effect=ServiceUnavailableError()), \
         patch.object(llm_gateway.time, "sleep"):
        try:
            llm_gateway.call_llm("gemini/test-model", f"failed prompt {uuid.uuid4()}")
        except llm_gateway.LLMGatewayError as exc:
            assert "All configured LLM providers failed" in str(exc)
            assert "gemini/test-model" in str(exc)
            assert "groq/test-model" in str(exc)
        else:
            raise AssertionError("Provider failures must not become a success-shaped response.")
