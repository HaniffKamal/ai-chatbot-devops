# ==============================================================================
# Automated Tests: POST /api/chat Endpoint & RAG Pipeline
# ==============================================================================
# Verifies:
#   1. Successful chat generation with context_used=True.
#   2. Input validation & boundary protection (empty, missing, and oversize strings).
#   3. Graceful degradation when upstream LLM engines fail (Rule 4.1).
#   4. RAG vector context retrieval accuracy.
# ==============================================================================

from unittest.mock import AsyncMock

from app.llm_client import LLMResult
from fastapi import status
from fastapi.testclient import TestClient


def test_chat_valid_message_returns_success(
    client: TestClient, mock_llm_success: LLMResult, monkeypatch
):
    """Verify that a valid user query returns 200 OK with context_used=True."""
    import app.main

    # Mock DualEngineLLM inference to run instantly without live GPU/cloud dependencies
    monkeypatch.setattr(
        app.main.dual_engine,
        "generate_response",
        AsyncMock(return_value=mock_llm_success),
    )

    payload = {"message": "What are Haniff's technical skills in DevOps and AI?"}
    response = client.post("/api/chat", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["context_used"] is True
    assert data["reply"] == mock_llm_success.text
    assert data["provider"] == "ollama"


def test_chat_empty_message_returns_422(client: TestClient):
    """Verify that empty message string is rejected by Pydantic schema (min_length=1)."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_missing_message_returns_422(client: TestClient):
    """Verify that payload missing the 'message' field is rejected."""
    response = client.post("/api/chat", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_message_too_long_returns_422(client: TestClient):
    """Verify that messages exceeding 1000 characters are rejected (boundary protection)."""
    oversize_message = "A" * 1001
    response = client.post("/api/chat", json={"message": oversize_message})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_chat_graceful_degradation_when_llm_fails(
    client: TestClient, mock_llm_degraded: LLMResult, monkeypatch
):
    """Verify that if all LLM engines fail, API returns status='degraded' without 500 error."""
    import app.main

    monkeypatch.setattr(
        app.main.dual_engine,
        "generate_response",
        AsyncMock(return_value=mock_llm_degraded),
    )

    payload = {"message": "Tell me about Haniff"}
    response = client.post("/api/chat", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "degraded"
    assert data["provider"] == "system-fallback"


def test_rag_pipeline_retrieval(client: TestClient):
    """Verify that RAGPipeline retrieves relevant markdown context for skills query."""
    import app.main

    assert app.main.rag_pipeline is not None, "RAG pipeline should be initialized"
    query = "What are Haniff technical skills in DevOps and AI?"
    context = app.main.rag_pipeline.retrieve_context(query, n_results=5)

    assert len(context) > 0, "Expected non-empty RAG context"
    assert (
        "DevOps" in context or "Docker" in context or "AWS" in context
    ), "Expected DevOps or Cloud tools in retrieved context"
