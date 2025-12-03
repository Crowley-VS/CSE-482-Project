"""Application configuration using Pydantic settings."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/economic_events_db",
        description="PostgreSQL database connection string"
    )

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "EconomicEventBot/1.0"

    # Reddit Selenium Auth
    REDDIT_USERNAME: str = ""
    REDDIT_PASSWORD: str = ""
    # Skip login and collect public posts only
    REDDIT_COLLECT_WITHOUT_LOGIN: bool = False

    # Twitter API
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""

    # Twitter Selenium Auth
    TWITTER_USERNAME: str = ""
    TWITTER_PASSWORD: str = ""

    # Selenium
    SELENIUM_HEADLESS: bool = True
    # Connect to existing Chrome instead of creating new instance
    USE_EXISTING_CHROME_SESSION: bool = False
    CHROME_DEBUG_PORT: int = 9222  # Port for Chrome remote debugging

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # Data Collection
    COLLECTION_INTERVAL_HOURS: int = 1
    MAX_POSTS_PER_SUBREDDIT: int = 100
    MAX_TWEETS_PER_QUERY: int = 100

    # Economic Keywords
    ECONOMIC_KEYWORDS: str = "CPI,inflation,interest rate,Fed,Federal Reserve,jobs report,unemployment,GDP,trade deficit,tariff,recession,employment,FOMC,monetary policy,fiscal policy"

    # Subreddits
    SUBREDDITS: str = "Economics,WallStreetBets,Finance"

    # OpenAI Configuration
    OPENAI_API_KEY: str = ""

    # Event Detection
    SPIKE_THRESHOLD: float = 2.5  # Standard deviations
    TIME_WINDOW_HOURS: int = 24
    MIN_POSTS_FOR_EVENT: int = 5

    # Scheduler
    SCHEDULER_ACTIVE: bool = False

    @field_validator('CORS_ORIGINS', 'ECONOMIC_KEYWORDS', 'SUBREDDITS')
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
