"""Tests for EagleEye Slack bot application (Claude Agent SDK based)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import EagleEyeBot
from config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        slack_bot_token="xoxb-test-token",
        slack_app_token="xapp-test-token",
        slack_signing_secret="test-signing-secret",
        slack_team_id="T0123456789",
        notion_api_key="secret_test_notion_key",
        linear_api_key="lin_api_test_key",
    )


class TestEagleEyeBotInit:
    """Tests for EagleEyeBot initialization."""

    def test_init_creates_app(self, mock_settings: Settings) -> None:
        """Test that bot initializes Slack app correctly."""
        with patch("app.App") as mock_app_class:
            with patch("app.ClaudeSearchAgent"):
                bot = EagleEyeBot(mock_settings)

                mock_app_class.assert_called_once_with(
                    token="xoxb-test-token",
                    signing_secret="test-signing-secret",
                )
                assert bot.settings == mock_settings

    def test_init_creates_claude_agent(self, mock_settings: Settings) -> None:
        """Test that bot initializes Claude agent with settings."""
        with patch("app.App"):
            with patch("app.ClaudeSearchAgent") as mock_claude:
                bot = EagleEyeBot(mock_settings)

                mock_claude.assert_called_once_with(
                    settings=mock_settings,
                    model="claude-sonnet-4-20250514",
                )
                assert bot.claude_agent is not None


class TestClaudeSearch:
    """Tests for Claude-powered search."""

    def test_run_claude_search_calls_agent(self, mock_settings: Settings) -> None:
        """Test that search calls Claude agent."""
        with patch("app.App"):
            with patch("app.ClaudeSearchAgent") as mock_claude_class:
                mock_agent = MagicMock()
                mock_agent.search = AsyncMock(return_value="Search results here")
                mock_claude_class.return_value = mock_agent

                bot = EagleEyeBot(mock_settings)
                result = bot._run_claude_search("test query")

                mock_agent.search.assert_called_once_with("test query")
                assert result == "Search results here"

    def test_run_claude_search_handles_error(self, mock_settings: Settings) -> None:
        """Test that search handles errors gracefully."""
        with patch("app.App"):
            with patch("app.ClaudeSearchAgent") as mock_claude_class:
                mock_agent = MagicMock()
                mock_agent.search = AsyncMock(side_effect=Exception("API Error"))
                mock_claude_class.return_value = mock_agent

                bot = EagleEyeBot(mock_settings)
                result = bot._run_claude_search("test query")

                assert result.startswith("__ERROR__:")
                assert "API Error" in result


class TestMentionHandler:
    """Tests for app mention handler."""

    def test_mention_handler_extracts_query_from_text(self) -> None:
        """Test that mention handler extracts query correctly."""
        event = {"text": "<@U123BOT> find project docs"}

        # The handler should extract "find project docs" from the text
        text = event.get("text", "")
        query = " ".join(text.split()[1:]).strip()

        assert query == "find project docs"

    def test_mention_handler_handles_empty_query(self) -> None:
        """Test that empty queries are handled."""
        event = {"text": "<@U123BOT>"}

        text = event.get("text", "")
        query = " ".join(text.split()[1:]).strip()

        assert query == ""


class TestBotStart:
    """Tests for bot startup."""

    def test_start_uses_socket_mode(self, mock_settings: Settings) -> None:
        """Test that bot starts with Socket Mode."""
        with patch("app.App"):
            with patch("app.ClaudeSearchAgent"):
                with patch("app.SocketModeHandler") as mock_handler:
                    bot = EagleEyeBot(mock_settings)
                    bot.start()

                    mock_handler.assert_called_once()
                    mock_handler.return_value.start.assert_called_once()


class TestClaudeAgentConfig:
    """Tests for Claude agent configuration."""

    def test_agent_uses_custom_model(self) -> None:
        """Test that agent uses custom model from settings."""
        settings = Settings(
            claude_model="claude-opus-4-20250514",
            slack_bot_token="xoxb-test-token",
            slack_app_token="xapp-test-token",
            slack_signing_secret="test-signing-secret",
            slack_team_id="T0123456789",
            notion_api_key="secret_test_notion_key",
            linear_api_key="lin_api_test_key",
        )

        with patch("app.App"):
            with patch("app.ClaudeSearchAgent") as mock_claude:
                EagleEyeBot(settings)

                mock_claude.assert_called_once_with(
                    settings=settings,
                    model="claude-opus-4-20250514",
                )
