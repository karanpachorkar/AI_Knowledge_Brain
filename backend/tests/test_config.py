import pytest
from app.core.config import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.APPLICATION_ENV in ["development", "production", "test"]
    assert settings.APPLICATION_PORT == 8000
    assert "postgresql+asyncpg" in settings.async_database_url
    assert "redis://" in settings.computed_redis_url
    assert settings.CHAT_MODEL in ["qwen2.5:3b", "qwen2.5:7b"]
    assert settings.EMBEDDING_MODEL == "bge-m3"



def test_settings_custom_database_url():
    settings = Settings(DATABASE_URL="postgresql://custom_user:pass@custom_host:5432/custom_db")
    assert settings.async_database_url == "postgresql+asyncpg://custom_user:pass@custom_host:5432/custom_db"
