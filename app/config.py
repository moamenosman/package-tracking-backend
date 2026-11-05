from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", # Instructs Pydantic to read environment variables from the .env
        env_file_encoding="utf-8",
        extra="ignore", # ignore any extra variables in your .env file that aren't defined in the Settings class
    )


# caches the result of Settings() the first time it is called.
@lru_cache
def get_settings() -> Settings:
    return Settings()