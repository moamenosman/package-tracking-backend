from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # SecretStr is to prevent accidental credential leakage in stdout or log files, it outputs SecretStr('**********')
    # and this field is mandatory, so the project will throw error if it is missing from the .env file
    mongodb_uri: SecretStr
    
    mongodb_database: str = Field(
        default="PulseShip",
        min_length=1,
    )


    session_secret: SecretStr
    session_https_only: bool = False
    session_max_age: int = Field(default=28800, gt=0)

    public_origin: str = "http://localhost:5173"
    api_origin: str = "http://127.0.0.1:8000"


    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", # Instructs Pydantic to read environment variables from the .env
        env_file_encoding="utf-8",
        extra="ignore", # ignore any extra variables in your .env file that aren't defined in the Settings class
    )


    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError(
                "SESSION_SECRET must contain at least 32 characters."
            )
        return value


# caches the result of Settings() the first time it is called.
@lru_cache
def get_settings() -> Settings:
    return Settings()