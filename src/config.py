"""kbgen settings — single source of truth for env-driven config."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service
    port: int = Field(default=8004, validation_alias="PORT")
    backend_port: int | None = Field(default=None, validation_alias="BACKEND_PORT")
    log_level: str = Field(default="INFO")

    # Database — shared with conversational-assistant (agentic_commerce)
    database_url: str = Field(
        default="postgresql+asyncpg://agentic:agentic_dev_2026@localhost:5432/agentic_commerce",
        validation_alias="DATABASE_URL",
    )
    db_schema: str = "kb"

    # OpenAI
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1", validation_alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", validation_alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=1536, validation_alias="PGVECTOR_EMBED_DIM")

    # Chunking + retrieval defaults (also persisted in kb.settings, overridable at runtime)
    chunk_size_tokens: int = Field(default=500, validation_alias="CHUNK_SIZE_TOKENS")
    chunk_overlap: int = Field(default=60, validation_alias="CHUNK_OVERLAP")
    dedup_threshold: float = Field(default=0.82, validation_alias="DEDUP_THRESHOLD")

    # ITSM
    itsm_adapter: str = Field(default="mock", validation_alias="ITSM_ADAPTER")
    glpi_url: str = Field(default="http://localhost:9080/apirest.php", validation_alias="GLPI_URL")
    glpi_app_token: str = Field(default="", validation_alias="GLPI_APP_TOKEN")
    glpi_user_token: str = Field(default="", validation_alias="GLPI_USER_TOKEN")

    # Scheduler
    poll_interval_s: int = Field(default=60, validation_alias="POLL_INTERVAL_S")

    # First-boot behaviour (for compose demos — off by default so production
    # deploys don't seed a customer's real ITSM).
    auto_seed_itsm: bool = Field(default=False, validation_alias="AUTO_SEED_ITSM")

    @property
    def effective_port(self) -> int:
        return self.backend_port or self.port


@lru_cache
def get_settings() -> Settings:
    return Settings()
