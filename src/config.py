from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    GOOGLE_API_KEY: str

    MAX_SLIDES: int = 20
    MIN_SLIDES: int = 1

    OUTPUT_DIR: Path = Path("generated")
    FILE_TTL_SECONDS: int = 3600

    RATE_LIMIT_PER_MINUTE: int = 10

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://slide-forge123.vercel.app/",
    ]

    @field_validator("MAX_SLIDES")
    @classmethod
    def max_slides_in_range(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("MAX_SLIDES must be between 1 and 50")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def log_level_valid(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return v.upper()


settings = Settings()
