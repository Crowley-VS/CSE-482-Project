"""Application configuration using Pydantic settings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/economic_events_db",
        description="PostgreSQL database connection string"
    )

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @field_validator('CORS_ORIGINS')
    @classmethod
    def parse_comma_separated(cls, v: str) -> List[str]:
        """Parse comma-separated strings from .env into lists."""
        return [item.strip() for item in v.split(',')]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


# Global settings instance
settings = Settings()
