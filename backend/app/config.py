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

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Core Application Environment
    # --------------------------------------------------------------------------
    # Options: "development", "staging", "production"
    ENVIRONMENT: str = "development"

    # --------------------------------------------------------------------------
    # Local Ollama Inference Engine (Primary Provider)
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
    # EMBEDDING_MODEL: Vector embedding model running in Ollama on the RTX 3060 GPU.
    # CHROMA_PERSIST_DIR: Container path where ChromaDB's SQLite database is stored.
    #                     (Mounted to a Docker Named Volume so vectors survive restarts).
    # KNOWLEDGE_DATA_DIR: Directory containing raw portfolio markdown files for ingestion.
    EMBEDDING_MODEL: str = "nomic-embed-text"
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    KNOWLEDGE_DATA_DIR: str = "/app/data"

    # --------------------------------------------------------------------------
    # Cloud Groq Inference Engine (High-Speed Fallback Provider)
    # --------------------------------------------------------------------------
    # GROQ_API_KEY: Secret API key for Groq Cloud. Kept empty by default; loaded
    #               dynamically from .env at runtime.
    # GROQ_MODEL: Fast, open-source model running on Groq's custom LPU hardware.
    # GROQ_BASE_URL: Standard OpenAI-compatible REST endpoint for Groq API.
    # GROQ_TIMEOUT: Maximum seconds to wait for cloud response before degradation.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT: float = 30.0

    # --------------------------------------------------------------------------
    # Networking & Cross-Origin Resource Sharing (CORS)
    # --------------------------------------------------------------------------
    # Comma-separated list of allowed origins. Permits both local browser testing
    # and cross-origin requests from the developer's external portfolio website.
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80,https://haniffkamal.my"

    # --------------------------------------------------------------------------
    # Dynamic Computed Properties (@property)
    # --------------------------------------------------------------------------
    @property
    def allowed_origins_list(self) -> list[str]:
        """
        Dynamically splits the comma-separated ALLOWED_ORIGINS string into a clean
        Python list of trimmed URLs required by FastAPI's CORSMiddleware.
        """
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

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
