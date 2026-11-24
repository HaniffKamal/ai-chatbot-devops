# ==============================================================================
# Automated Tests: GET /metrics Endpoint
# ==============================================================================
# Verifies:
#   1. HTTP 200 OK and Prometheus text exposition format.
#   2. The RAG index gauge is exposed.
#   3. The endpoint is excluded from the OpenAPI schema.
# ==============================================================================

from fastapi import status
from fastapi.testclient import TestClient


def test_metrics_returns_200(client: TestClient):
    """Verify that GET /metrics responds with 200 OK."""
    response = client.get("/metrics")
    assert response.status_code == status.HTTP_200_OK


def test_metrics_exposes_rag_index_gauge(client: TestClient):
    """Verify that the RAG chunk gauge is present in the exposition."""
    response = client.get("/metrics")
    assert "chatbot_rag_indexed_chunks" in response.text


def test_metrics_endpoint_not_in_openapi(client: TestClient):
    """Verify that /metrics is hidden from the public schema."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    assert "/metrics" not in response.json()["paths"]
