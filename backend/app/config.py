# ==============================================================================
# Application Configuration: Pydantic Settings (12-Factor Compliant)
# ==============================================================================
# Responsibilities:
#   1. Loads environment variables from .env file or host environment.
#   2. Validates types and provides production-ready fallback defaults.
#   3. Exposes configuration properties for CORS and LLM providers.
# ==============================================================================

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Environment
    ENVIRONMENT: str = "development"

    # Local Ollama Inference Engine (Primary)
    OLLAMA_HOST: str = "http://ollama:11434"
    DEFAULT_MODEL: str = "llama3.2:1b"
    OLLAMA_TIMEOUT: float = 60.0
    OLLAMA_CONNECT_TIMEOUT: float = 5.0

    # Embedded ChromaDB & RAG Knowledge Store
    EMBEDDING_MODEL: str = "nomic-embed-text"
    CHROMA_PERSIST_DIR: str = "/app/chroma_db"
    KNOWLEDGE_DATA_DIR: str = "/app/data"

    # Cloud Groq Inference Engine (Fallback)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT: float = 30.0

    # Networking & Security
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:80,https://haniffkamal.my"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Split comma-separated origins into a validated list for CORSMiddleware."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def is_groq_enabled(self) -> bool:
        """Check if a non-empty Groq API key is configured."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())


# Global settings singleton
settings = Settings()
