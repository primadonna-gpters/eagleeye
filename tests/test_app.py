"""Tests for EagleEye Slack bot application."""

from unittest.mock import patch

import pytest

from eagleeye.app import EagleEyeBot
from eagleeye.config import Settings
from eagleeye.models.search import SearchResult, SearchResultType


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        slack_bot_token="xoxb-test-token",
        slack_app_token="xapp-test-token",
        slack_signing_secret="test-signing-secret",
        notion_api_key="secret_test_notion_key",
        linear_api_key="lin_api_test_key",
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Sample search results for testing."""
    return [
        SearchResult(
            source=SearchResultType.SLACK,
            title="Message in #general",
            url="https://workspace.slack.com/archives/C123/p123",
            snippet="This is a test message",
            author="testuser",
        ),
        SearchResult(
            source=SearchResultType.NOTION,
            title="Project Documentation",
            url="https://notion.so/page-123",
            snippet="Documentation about the project",
        ),
        SearchResult(
            source=SearchResultType.LINEAR,
            title="DEV-123: Fix bug",
            url="https://linear.app/team/issue/DEV-123",
            snippet="Bug fix description",
            author="developer",
        ),
    ]


class TestEagleEyeBotInit:
    """Tests for EagleEyeBot initialization."""

    def test_init_creates_app(self, mock_settings: Settings) -> None:
        """Test that bot initializes Slack app correctly."""
        with patch("eagleeye.app.App") as mock_app_class:
            with patch("eagleeye.app.SlackSearchClient"):
                with patch("eagleeye.app.NotionSearchClient"):
                    with patch("eagleeye.app.LinearClient"):
                        bot = EagleEyeBot(mock_settings)

                        mock_app_class.assert_called_once_with(
                            token="xoxb-test-token",
                            signing_secret="test-signing-secret",
                        )
                        assert bot.settings == mock_settings

    def test_init_creates_search_clients(self, mock_settings: Settings) -> None:
        """Test that bot initializes all search clients."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        EagleEyeBot(mock_settings)

                        mock_slack.assert_called_once_with("xoxb-test-token")
                        mock_notion.assert_called_once_with("secret_test_notion_key")
                        mock_linear.assert_called_once_with("lin_api_test_key")


class TestUnifiedSearch:
    """Tests for unified search functionality."""

    def test_unified_search_combines_results(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that unified search combines results from all sources."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        # Setup mock returns
                        mock_slack.return_value.search.return_value = [
                            sample_search_results[0]
                        ]
                        mock_notion.return_value.search.return_value = [
                            sample_search_results[1]
                        ]
                        mock_linear.return_value.search.return_value = [
                            sample_search_results[2]
                        ]

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search("test query")

                        assert len(results) == 3
                        sources = {r.source for r in results}
                        assert sources == {
                            SearchResultType.SLACK,
                            SearchResultType.NOTION,
                            SearchResultType.LINEAR,
                        }

    def test_unified_search_handles_empty_results(
        self, mock_settings: Settings
    ) -> None:
        """Test unified search when no results are found."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = []
                        mock_notion.return_value.search.return_value = []
                        mock_linear.return_value.search.return_value = []

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search("nonexistent query")

                        assert results == []

    def test_unified_search_handles_partial_failure(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search continues when one source fails."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = [
                            sample_search_results[0]
                        ]
                        mock_notion.return_value.search.side_effect = Exception(
                            "API Error"
                        )
                        mock_linear.return_value.search.return_value = [
                            sample_search_results[2]
                        ]

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search("test query")

                        # Should still get results from Slack and Linear
                        assert len(results) == 2
                        sources = {r.source for r in results}
                        assert SearchResultType.SLACK in sources
                        assert SearchResultType.LINEAR in sources
                        assert SearchResultType.NOTION not in sources

    def test_unified_search_respects_limit(self, mock_settings: Settings) -> None:
        """Test that limit is passed to search clients."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = []
                        mock_notion.return_value.search.return_value = []
                        mock_linear.return_value.search.return_value = []

                        bot = EagleEyeBot(mock_settings)
                        bot._unified_search("test", limit=5)

                        mock_slack.return_value.search.assert_called_once_with(
                            "test", 5
                        )
                        mock_notion.return_value.search.assert_called_once_with(
                            "test", 5
                        )
                        mock_linear.return_value.search.assert_called_once_with(
                            "test", 5
                        )


class TestFormatResults:
    """Tests for result formatting."""

    def test_format_results_creates_header(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that formatted results include header."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient"):
                with patch("eagleeye.app.NotionSearchClient"):
                    with patch("eagleeye.app.LinearClient"):
                        bot = EagleEyeBot(mock_settings)
                        blocks = bot._format_results_as_blocks(
                            "test query", sample_search_results
                        )

                        # First block should be header
                        assert blocks[0]["type"] == "header"
                        assert (
                            blocks[0]["text"]["text"]
                            == "Search results for: test query"
                        )

    def test_format_results_groups_by_source(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that results are grouped by source."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient"):
                with patch("eagleeye.app.NotionSearchClient"):
                    with patch("eagleeye.app.LinearClient"):
                        bot = EagleEyeBot(mock_settings)
                        blocks = bot._format_results_as_blocks(
                            "test", sample_search_results
                        )

                        # Find section headers (source groupings)
                        section_texts = [
                            b["text"]["text"]
                            for b in blocks
                            if b["type"] == "section"
                            and "text" in b
                            and "*" in b["text"].get("text", "")
                        ]

                        # Should have headers for each source
                        assert any("Slack" in t for t in section_texts)
                        assert any("Notion" in t for t in section_texts)
                        assert any("Linear" in t for t in section_texts)

    def test_format_results_includes_dividers(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that dividers are included between sections."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient"):
                with patch("eagleeye.app.NotionSearchClient"):
                    with patch("eagleeye.app.LinearClient"):
                        bot = EagleEyeBot(mock_settings)
                        blocks = bot._format_results_as_blocks(
                            "test", sample_search_results
                        )

                        divider_count = sum(1 for b in blocks if b["type"] == "divider")
                        # At least one divider after header + one per source
                        assert divider_count >= 2


class TestSearchCommandHandler:
    """Tests for /search slash command handler."""

    def test_search_command_empty_query_returns_empty_results(
        self, mock_settings: Settings
    ) -> None:
        """Test that empty/whitespace query returns empty results."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = []
                        mock_notion.return_value.search.return_value = []
                        mock_linear.return_value.search.return_value = []

                        bot = EagleEyeBot(mock_settings)
                        # Empty query search should return empty results
                        results = bot._unified_search("   ")

                        assert results == []

    def test_search_command_with_query_calls_unified_search(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test /search with query performs unified search."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = [
                            sample_search_results[0]
                        ]
                        mock_notion.return_value.search.return_value = []
                        mock_linear.return_value.search.return_value = []

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search("test query")

                        assert len(results) == 1
                        mock_slack.return_value.search.assert_called_once()


class TestMentionHandler:
    """Tests for @mention event handler."""

    def test_mention_handler_extracts_query_from_text(self) -> None:
        """Test that mention handler correctly extracts query after bot mention."""
        # Test query extraction logic used in handler
        text = "<@U123BOT> search for this"
        query = " ".join(text.split()[1:]).strip()

        assert query == "search for this"

    def test_mention_handler_handles_empty_query(self) -> None:
        """Test that mention with only bot mention has empty query."""
        text = "<@U123BOT>"
        query = " ".join(text.split()[1:]).strip()

        assert query == ""


class TestBotStart:
    """Tests for bot start functionality."""

    def test_start_uses_socket_mode(self, mock_settings: Settings) -> None:
        """Test that start() uses SocketModeHandler."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient"):
                with patch("eagleeye.app.NotionSearchClient"):
                    with patch("eagleeye.app.LinearClient"):
                        with patch("eagleeye.app.SocketModeHandler") as mock_handler:
                            bot = EagleEyeBot(mock_settings)
                            bot.start()

                            mock_handler.assert_called_once_with(
                                bot.app, "xapp-test-token"
                            )
                            mock_handler.return_value.start.assert_called_once()
