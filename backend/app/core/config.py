"""Application configuration using Pydantic settings."""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


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
    
    # Twitter API
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Data Collection
    COLLECTION_INTERVAL_HOURS: int = 1
    MAX_POSTS_PER_SUBREDDIT: int = 100
    MAX_TWEETS_PER_QUERY: int = 100
    
    # Economic Keywords
    ECONOMIC_KEYWORDS: List[str] = [
        "CPI", "inflation", "interest rate", "Fed", "Federal Reserve",
        "jobs report", "unemployment", "GDP", "trade deficit", "tariff",
        "recession", "employment", "FOMC", "monetary policy", "fiscal policy"
    ]
    
    # Subreddits
    SUBREDDITS: List[str] = ["Economics", "WallStreetBets", "Finance"]
    
    # Event Detection
    SPIKE_THRESHOLD: float = 2.5  # Standard deviations
    TIME_WINDOW_HOURS: int = 24
    MIN_POSTS_FOR_EVENT: int = 5
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True
        
        # Handle comma-separated strings from .env
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name in ['CORS_ORIGINS', 'ECONOMIC_KEYWORDS', 'SUBREDDITS']:
                return [item.strip() for item in raw_val.split(',')]
            return raw_val


# Global settings instance
settings = Settings()
