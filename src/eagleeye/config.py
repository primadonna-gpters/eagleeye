"""Configuration settings for EagleEye."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Slack Bot (for Slack Bolt app)
    slack_bot_token: str
    slack_app_token: str  # For Socket Mode
    slack_signing_secret: str

    # MCP Server API Keys
    # Slack MCP uses the same bot token
    notion_api_key: str
    linear_api_key: str

    # Optional: Enable/disable specific MCP servers
    enable_slack_mcp: bool = True
    enable_notion_mcp: bool = True
    enable_linear_mcp: bool = True


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()  # type: ignore[call-arg]
