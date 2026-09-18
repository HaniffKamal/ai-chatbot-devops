# ==============================================================================
# Dual-Engine LLM Client: Seamless Primary (Ollama) + Cloud Fallback (Groq)
# ==============================================================================
# Architecture:
#   1. Primary Engine: Local Ollama container with NVIDIA RTX GPU pass-through.
#   2. Fallback Engine: High-speed Cloud Groq API (OpenAI-compatible LPU inference).
#   3. Graceful Degradation: Friendly degraded message if all providers fail (Rule 4.1).
#   4. Connection Pooling: Persistent async HTTP connection pools for minimal latency.
# ==============================================================================

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from app.config import Settings, settings

logger = logging.getLogger("chatbot-llm")


@dataclass(frozen=True)
class LLMResult:
    """Standardized inference response payload across all providers."""

    text: str
    model: str
    provider: str  # "ollama" | "groq" | "system-fallback"
    success: bool
    error_detail: str | None = None


class DualEngineLLM:
    """
    Manages dual-engine LLM inference lifecycle, upstream health verification,
    and automatic failover between local and cloud providers.
    """

    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self._ollama_client: httpx.AsyncClient | None = None
        self._groq_client: httpx.AsyncClient | None = None

    def initialize(self) -> None:
        """Initialize async HTTP connection pools with custom timeouts."""
        logger.info(
            "Initializing Dual-Engine LLM client pool (Primary: %s, Groq Fallback: %s)",
            self.settings.OLLAMA_HOST,
            "Enabled" if self.settings.is_groq_enabled else "Disabled",
        )

        self._ollama_client = httpx.AsyncClient(
            base_url=self.settings.OLLAMA_HOST,
            timeout=httpx.Timeout(
                self.settings.OLLAMA_TIMEOUT,
                connect=self.settings.OLLAMA_CONNECT_TIMEOUT,
            ),
        )

        self._groq_client = httpx.AsyncClient(
            base_url=self.settings.GROQ_BASE_URL,
            timeout=httpx.Timeout(
                self.settings.GROQ_TIMEOUT,
                connect=5.0,
            ),
        )

    async def aclose(self) -> None:
        """Gracefully terminate open connection pools on application shutdown."""
        logger.info("Closing Dual-Engine LLM HTTP connection pools...")
        if self._ollama_client:
            await self._ollama_client.aclose()
        if self._groq_client:
            await self._groq_client.aclose()

    async def check_ollama_health(self) -> bool:
        """Probe local Ollama daemon for operational readiness."""
        if not self._ollama_client:
            return False
        try:
            response = await self._ollama_client.get("/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama health check probe failed: %s", exc)
            return False

    async def check_groq_health(self) -> bool:
        """Probe Groq cloud API for authentication and connectivity."""
        if not self._groq_client or not self.settings.is_groq_enabled:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.settings.GROQ_API_KEY}"}
            response = await self._groq_client.get(
                "/models", headers=headers, timeout=5.0
            )
            return response.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq health check probe failed: %s", exc)
            return False

    async def _query_ollama(
        self, prompt: str, system_prompt: str, model_name: str
    ) -> str:
        """Dispatch inference request to local Ollama container."""
        if not self._ollama_client:
            raise RuntimeError("Ollama client pool is not initialized")

        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }

        logger.info("Dispatching prompt to Ollama model '%s'", model_name)
        response = await self._ollama_client.post("/api/generate", json=payload)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        reply_text = str(data.get("response", "")).strip()

        if not reply_text:
            raise ValueError("Ollama returned an empty response string")

        return reply_text

    async def _query_groq(self, prompt: str, system_prompt: str) -> str:
        """Dispatch OpenAI-compatible chat completion request to Groq Cloud."""
        if not self._groq_client:
            raise RuntimeError("Groq client pool is not initialized")
        if not self.settings.is_groq_enabled:
            raise ValueError("Groq API key is not configured in environment")

        headers = {
            "Authorization": f"Bearer {self.settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.settings.GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        logger.info(
            "Dispatching fallback prompt to Groq Cloud model '%s'",
            self.settings.GROQ_MODEL,
        )
        response = await self._groq_client.post(
            "/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Groq API returned an empty choices list")

        message_obj = choices[0].get("message", {})
        reply_text = str(message_obj.get("content", "")).strip()

        if not reply_text:
            raise ValueError("Groq API returned an empty content string")

        return reply_text

    async def generate_response(
        self, prompt: str, system_prompt: str = "", model: str | None = None
    ) -> LLMResult:
        """
        Execute dual-engine inference with automatic failover and graceful degradation.
        1. Attempt primary local Ollama.
        2. On failure/timeout, fall back to Groq Cloud API.
        3. On total failure, return friendly degraded message (Rule 4.1).
        """
        target_model = model or self.settings.DEFAULT_MODEL
        ollama_error: str | None = None

        # ----------------------------------------------------------------------
        # 1. Primary Engine: Local Ollama
        # ----------------------------------------------------------------------
        try:
            reply = await self._query_ollama(
                prompt=prompt,
                system_prompt=system_prompt,
                model_name=target_model,
            )
            return LLMResult(
                text=reply,
                model=target_model,
                provider="ollama",
                success=True,
            )
        except Exception as exc:  # noqa: BLE001
            ollama_error = str(exc)
            logger.warning(
                "Primary engine (Ollama) failed: %s. Initiating fallback to Groq Cloud...",
                exc,
            )

        # ----------------------------------------------------------------------
        # 2. Fallback Engine: Cloud Groq
        # ----------------------------------------------------------------------
        groq_error: str | None = None
        if self.settings.is_groq_enabled:
            try:
                reply = await self._query_groq(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
                logger.info(
                    "Fallback to Groq succeeded using model '%s'",
                    self.settings.GROQ_MODEL,
                )
                return LLMResult(
                    text=reply,
                    model=self.settings.GROQ_MODEL,
                    provider="groq",
                    success=True,
                )
            except Exception as exc:  # noqa: BLE001
                groq_error = str(exc)
                logger.error("Cloud fallback (Groq) also failed: %s", exc)
        else:
            groq_error = "GROQ_API_KEY is not configured"
            logger.warning("Groq fallback skipped: %s", groq_error)

        # ----------------------------------------------------------------------
        # 3. Graceful Degradation (Rule 4.1)
        # ----------------------------------------------------------------------
        logger.error(
            "Dual-engine inference failed completely. (Ollama: %s | Groq: %s)",
            ollama_error,
            groq_error,
        )
        return LLMResult(
            text=(
                "I am temporarily experiencing high service demand or maintenance. "
                "Please try asking your question again in a moment, or reach out directly to Haniff Kamal."
            ),
            model="system-degraded",
            provider="system-fallback",
            success=False,
            error_detail=f"Ollama: {ollama_error} | Groq: {groq_error}",
        )
