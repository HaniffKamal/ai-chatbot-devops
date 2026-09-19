# ==============================================================================
# Automated Tests: GET /health Endpoint
# ==============================================================================
# Verifies:
#   1. HTTP 200 OK status code.
#   2. Full HealthResponse schema compliance.
#   3. Active ChromaDB RAG chunk indexing count.
# ==============================================================================

from fastapi import status
from fastapi.testclient import TestClient


def test_health_returns_200_and_status_ok(client: TestClient):
    """Verify that GET /health responds with 200 OK and status='ok'."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"


def test_health_contains_required_fields(client: TestClient):
    """Verify that all telemetry and configuration fields exist in response."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    required_fields = [
        "status",
        "ollama_connected",
        "groq_configured",
        "groq_connected",
        "configured_model",
        "fallback_model",
        "rag_indexed_chunks",
    ]
    for field in required_fields:
        assert field in data, f"Missing required health field: '{field}'"


def test_health_reports_positive_rag_chunks(client: TestClient):
    """Verify that the embedded ChromaDB knowledge base has indexed chunks."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert (
        data["rag_indexed_chunks"] > 0
    ), "Expected at least 1 indexed chunk in knowledge base"
