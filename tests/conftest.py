"""
Test harness: hermetic by construction.

* Dummy credentials are set BEFORE any application module is imported. The application calls load_dotenv(), which never
  overrides variables that already exist, so a developer's real .env keys cannot leak into a test run.
* Supabase points at an unresolvable host and every real network connection raises, so a test that forgets to mock a
  dependency FAILS instead of silently calling a real provider.
* The web-search client (DDGS) is replaced by a stub that raises.
"""
import os
import socket

INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"     # opt-in: real providers / a real (staging) database, see tests/integration

if not INTEGRATION:
    os.environ["SUPABASE_URL"] = "http://supabase.invalid"
    os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"
    os.environ["GEMINI_API_KEY"] = "test-gemini-key"
    os.environ["GROQ_API_KEY"] = "test-groq-key"
    os.environ["OPENROUTER_API_KEY"] = "test-openrouter-key"
    os.environ["ADMIN_EMAILS"] = "admin@example.test"

import pytest  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """Integration tests never run by accident: they need RUN_INTEGRATION=1, and then ONLY they are meaningful."""
    skip = pytest.mark.skip(reason="integration test: set RUN_INTEGRATION=1 (staging credentials in the environment)")
    for item in items:
        in_integration_dir = "integration" in item.nodeid.replace("\\", "/").split("/")
        if in_integration_dir and not INTEGRATION:
            item.add_marker(skip)
        elif INTEGRATION and not in_integration_dir:
            item.add_marker(pytest.mark.skip(reason="unit tests are hermetic; run them without RUN_INTEGRATION"))


class NetworkBlocked(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    if INTEGRATION:
        yield
        return
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def _is_loopback(host) -> bool:
        return str(host) in ("127.0.0.1", "::1", "localhost", "0.0.0.0")

    def guarded_connect(self, address, *a, **k):
        # asyncio/anyio (TestClient) use loopback socketpairs internally; everything else is a real network call.
        if isinstance(address, tuple) and address and _is_loopback(address[0]):
            return real_connect(self, address, *a, **k)
        raise NetworkBlocked(f"real network access is not allowed in tests (connect to {address!r}): mock the dependency")

    def guarded_getaddrinfo(host, *a, **k):
        if _is_loopback(host):
            return real_getaddrinfo(host, *a, **k)
        raise NetworkBlocked(f"real DNS lookup is not allowed in tests ({host!r}): mock the dependency")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    yield


@pytest.fixture(autouse=True)
def _reset_state():
    from backend import rate_limit
    from ai_core import llm_gateway
    rate_limit.reset()
    llm_gateway._cache.clear()
    yield
    rate_limit.reset()
