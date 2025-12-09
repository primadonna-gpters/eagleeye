"""Configuration settings for EagleEye."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Slack Bot
    slack_bot_token: str
    slack_app_token: str  # For Socket Mode
    slack_signing_secret: str

    # Notion
    notion_api_key: str

    # Linear
    linear_api_key: str


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]
