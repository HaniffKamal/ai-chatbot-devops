import pytest
from pydantic import ValidationError

from app.config import LOCAL_DEV_ORIGINS, Settings


def test_development_uses_localhost_fallback() -> None:
    settings = Settings(_env_file=None, ENVIRONMENT="development")
    assert settings.ALLOWED_ORIGINS == LOCAL_DEV_ORIGINS


def test_production_rejects_localhost_only_origins() -> None:
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            ALLOWED_ORIGINS="http://localhost,http://localhost:80",
        )


def test_production_accepts_explicit_https_origins() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        ALLOWED_ORIGINS="https://haniffkamal.my,https://chatbot.haniffkamal.my",
    )
    assert settings.allowed_origins_list == [
        "https://haniffkamal.my",
        "https://chatbot.haniffkamal.my",
    ]
