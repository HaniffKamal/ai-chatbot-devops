# ==============================================================================
# Automated Tests: DualEngineLLM Client (Production Groq Path)
# ==============================================================================
# Verifies (AGENTS.md Rule 4.1):
#   1. Happy path: Groq is queried and its text is returned.
#   2. Malformed upstream payloads fail loudly instead of returning empty replies.
#   3. generate_response() uses Groq as the production primary engine.
#   4. Groq unreachable + Ollama disabled -> friendly degraded LLMResult
#      (never an exception, never a 500 to the client).
#   5. Missing GROQ_API_KEY degrades gracefully without any network call.
#   6. check_groq_health() reports connectivity and swallows probe failures.
#
# All HTTP traffic is faked in-process: these tests never touch a real network.
# ==============================================================================

from typing import Any

import httpx
import pytest

from app.config import Settings
from app.llm_client import DualEngineLLM


class _FakeResponse:
    """Minimal stand-in for httpx.Response (only the members the client uses)."""

    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError(f"upstream returned HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    """Async client double that records calls, or raises a preset error."""

    def __init__(
        self,
        response: _FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if self._error is not None:
            raise self._error
        assert self._response is not None, "fake client is missing a response"
        return self._response

    async def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if self._error is not None:
            raise self._error
        assert self._response is not None, "fake client is missing a response"
        return self._response


def _make_engine(
    api_key: str = "test-groq-key",
    ollama_host: str = "disabled",
) -> DualEngineLLM:
    """Build a production-like client: Groq primary, no Ollama fallback."""
    app_settings = Settings(
        ENVIRONMENT="production",
        LLM_PROVIDER="groq",
        GROQ_API_KEY=api_key,
        OLLAMA_HOST=ollama_host,
        ALLOWED_ORIGINS="https://chatbot.haniffkamal.my",
    )
    return DualEngineLLM(app_settings=app_settings)


async def test_query_groq_returns_generated_text() -> None:
    """Verify the Groq payload shape and that the reply text is trimmed."""
    engine = _make_engine()
    fake = _FakeAsyncClient(
        _FakeResponse({"choices": [{"message": {"content": "  Groq says hello  "}}]})
    )
    engine._groq_client = fake  # type: ignore[assignment]

    reply = await engine._query_groq(prompt="What is RAG?", system_prompt="Be concise.")

    assert reply == "Groq says hello"
    assert fake.calls[0]["url"] == "/chat/completions"
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer test-groq-key"

    messages = fake.calls[0]["json"]["messages"]
    assert messages[0] == {"role": "system", "content": "Be concise."}
    assert messages[-1] == {"role": "user", "content": "What is RAG?"}


async def test_query_groq_rejects_response_without_choices() -> None:
    """Verify a 200 response with no choices raises instead of returning ''."""
    engine = _make_engine()
    fake = _FakeAsyncClient(_FakeResponse({"choices": []}))
    engine._groq_client = fake  # type: ignore[assignment]

    with pytest.raises(ValueError, match="empty choices"):
        await engine._query_groq(prompt="hi", system_prompt="")


async def test_generate_response_uses_groq_as_primary() -> None:
    """Verify the production path returns provider='groq' on success."""
    engine = _make_engine()
    fake = _FakeAsyncClient(
        _FakeResponse({"choices": [{"message": {"content": "Grounded answer"}}]})
    )
    engine._groq_client = fake  # type: ignore[assignment]

    result = await engine.generate_response(prompt="Who is Haniff?")

    assert result.success is True
    assert result.provider == "groq"
    assert result.model == engine.settings.GROQ_MODEL
    assert result.text == "Grounded answer"


async def test_generate_response_degrades_when_groq_fails() -> None:
    """Verify Rule 4.1: upstream failure returns a friendly message, not an error."""
    engine = _make_engine()
    fake = _FakeAsyncClient(error=httpx.ConnectError("groq unreachable"))
    engine._groq_client = fake  # type: ignore[assignment]

    result = await engine.generate_response(prompt="Who is Haniff?")

    assert result.success is False
    assert result.provider == "system-fallback"
    assert "temporarily" in result.text.lower()
    assert result.error_detail is not None
    assert "groq unreachable" in result.error_detail


async def test_generate_response_degrades_without_api_key() -> None:
    """Verify a missing GROQ_API_KEY degrades without attempting any request."""
    engine = _make_engine(api_key="")

    result = await engine.generate_response(prompt="Who is Haniff?")

    assert result.success is False
    assert result.provider == "system-fallback"
    assert result.error_detail is not None
    assert "GROQ_API_KEY" in result.error_detail


async def test_check_groq_health_reports_connectivity() -> None:
    """Verify the health probe returns True on 200 and False when the call raises."""
    engine = _make_engine()
    healthy = _FakeAsyncClient(_FakeResponse({}, status_code=200))
    engine._groq_client = healthy  # type: ignore[assignment]
    assert await engine.check_groq_health() is True

    unhealthy = _FakeAsyncClient(error=httpx.ConnectError("down"))
    engine._groq_client = unhealthy  # type: ignore[assignment]
    assert await engine.check_groq_health() is False
