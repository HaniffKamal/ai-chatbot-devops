# ==============================================================================
# Pytest Test Fixtures & Configuration
# ==============================================================================
# Senior Guardrails:
#   1. Isolated Vector Store: Uses pytest's tmp_path_factory so tests never
#      pollute or mutate local/production ChromaDB storage.
#   2. Dynamic Path Resolution: Resolves data/ directory properly whether running
#      on the host system or inside a Docker container.
#   3. Deterministic Mocking: Provides mock fixtures for LLM responses so CI/CD
#      tests run in milliseconds without requiring a live GPU or API keys.
# ==============================================================================

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path for test execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings
from app.llm_client import LLMResult
from app.main import app

# Ensure knowledge base directory resolves properly on host or container
data_dir = os.path.abspath(os.path.join(backend_dir, "data"))
if os.path.isdir(data_dir):
    settings.KNOWLEDGE_DATA_DIR = data_dir


@pytest.fixture(scope="session")
def client(tmp_path_factory: pytest.TempPathFactory):
    """
    Session-scoped TestClient fixture for FastAPI application.
    Enters lifespan context, indexing test knowledge chunks into an isolated temp dir.
    """
    test_chroma_dir = str(tmp_path_factory.mktemp("test_chroma_db"))
    settings.CHROMA_PERSIST_DIR = test_chroma_dir

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_llm_success():
    """Returns a deterministic successful LLMResult."""
    return LLMResult(
        text="Haniff is an AI & DevOps Engineer specializing in AWS and MLOps.",
        model="llama3.2:1b",
        provider="ollama",
        success=True,
    )


@pytest.fixture
def mock_llm_degraded():
    """Returns a degraded LLMResult when all providers fail."""
    return LLMResult(
        text="The AI Assistant is temporarily at capacity. Please try again later.",
        model="none",
        provider="system-fallback",
        success=False,
        error_detail="All upstream engines unreachable",
    )
