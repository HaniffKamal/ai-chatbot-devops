# ==============================================================================
# Application Configuration: Pydantic Settings (12-Factor App Compliant)
# ==============================================================================
# Architecture & DevOps Guardrails:
#   1. Factor III Compliance: Strictly separates runtime config from source code.
#   2. Zero Hardcoded Secrets (Rule 1.1): Schema is defined here; sensitive keys
#      live strictly in the uncommitted .env file or cloud environment variables.
#   3. Strict Type Safety: Pydantic validates data types at boot time. If an
#      invalid value is passed, the container fails fast before serving traffic.
#   4. Dynamic Resolution Order:
#        a. OS Environment Variables (e.g. AWS / Docker CLI / Kubernetes)
#        b. Local .env file (for local development)
#        c. Hardcoded fallback defaults defined below
# ==============================================================================

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEV_ORIGINS = "http://localhost,http://localhost:80"


class Settings(BaseSettings):
    """
    Strongly-typed application settings schema.
    Acts as the single source of truth for the entire backend microservice.
    """

    # --------------------------------------------------------------------------
    # Pydantic Settings Configuration
    # --------------------------------------------------------------------------
    # - env_file: Automatically loads key-value pairs from .env on startup.
    # - env_file_encoding: UTF-8 for cross-platform Linux/Mac/Windows compatibility.
    # - extra="ignore": Silently ignores extra environment variables rather than
    #   crashing if other tools define variables in .env.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Core Application Environment & Provider Preference
    # --------------------------------------------------------------------------
    # ENVIRONMENT: "development", "staging", "production"
    # LLM_PROVIDER: "ollama" (local GPU for dev) or "groq" (cloud API for CPU host in prod)
    ENVIRONMENT: str = "development"
    LLM_PROVIDER: str = "ollama"

    # --------------------------------------------------------------------------
    # Local Ollama Inference Engine (Primary Provider in Local Dev)
    # --------------------------------------------------------------------------
    # OLLAMA_HOST: Internal Docker network DNS name and port for Ollama daemon.
    # DEFAULT_MODEL: Default lightweight instruction model to query locally.
    # OLLAMA_TIMEOUT: Maximum seconds to wait for generation before triggering fallback.
    # OLLAMA_CONNECT_TIMEOUT: Maximum seconds to establish TCP handshake before aborting.
    OLLAMA_HOST: str = "http://ollama:11434"
    DEFAULT_MODEL: str = "llama3.2:1b"
    OLLAMA_TIMEOUT: float = 60.0
    OLLAMA_CONNECT_TIMEOUT: float = 5.0

    # --------------------------------------------------------------------------
    # Embedded ChromaDB & RAG Knowledge Store
    # --------------------------------------------------------------------------
    # EMBEDDING_MODEL: In-process ONNX embedding model (all-MiniLM-L6-v2).
    #                  Runs 100% locally in FastAPI on pure CPU without Ollama dependency.
    # CHROMA_PERSIST_DIR: Container path where ChromaDB's SQLite database is stored.
    #                     (Mounted to a Docker Named Volume so vectors survive restarts).
    # KNOWLEDGE_DATA_DIR: Directory containing raw portfolio markdown files for ingestion.
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    KNOWLEDGE_DATA_DIR: str = "/app/data"

    # --------------------------------------------------------------------------
    # Cloud Groq Inference Engine (High-Speed Provider / Production Primary)
    # --------------------------------------------------------------------------
    # GROQ_API_KEY: Secret API key for Groq Cloud. Kept empty by default; loaded
    #               dynamically from .env at runtime.
    # GROQ_MODEL: Official ultra-fast model running on Groq's custom LPU hardware.
    # GROQ_BASE_URL: Standard OpenAI-compatible REST endpoint for Groq API.
    # GROQ_TIMEOUT: Maximum seconds to wait for cloud response before degradation.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT: float = 30.0

    # --------------------------------------------------------------------------
    # Networking & Cross-Origin Resource Sharing (CORS)
    # --------------------------------------------------------------------------
    # Comma-separated list of allowed origins. Local-development fallback only;
    # production origins are supplied by the environment (.env rendered by Ansible).
    ALLOWED_ORIGINS: str = LOCAL_DEV_ORIGINS

    @model_validator(mode="after")
    def validate_production_origins(self) -> "Settings":
        """
        Fail fast if production boots with the local development fallback, rather
        than silently serving a broken CORS policy.
        """
        if self.ENVIRONMENT == "production" and not any(
            origin.startswith("https://") for origin in self.allowed_origins_list
        ):
            raise ValueError(
                "ALLOWED_ORIGINS must include at least one https origin when "
                "ENVIRONMENT=production (rendered by Ansible from .env.j2)."
            )
        return self

    # --------------------------------------------------------------------------
    # Dynamic Computed Properties (@property)
    # --------------------------------------------------------------------------
    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Dynamically splits the comma-separated ALLOWED_ORIGINS string into a clean
        Python list of trimmed URLs required by FastAPI's CORSMiddleware.
        """
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_groq_enabled(self) -> bool:
        """
        Evaluates whether a valid, non-empty Groq API key is present in the environment.
        Used by the DualEngineLLM client to decide whether cloud failover is available.
        """
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())


# ------------------------------------------------------------------------------
# Global Settings Singleton
# ------------------------------------------------------------------------------
# Instantiated once at application startup. Modules import `settings` directly
# (e.g. `from app.config import settings`) for typed autocomplete and zero overhead.
settings = Settings()
