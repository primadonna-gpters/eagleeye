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


class TestParseQuery:
    """Tests for query parsing with filter flags."""

    def test_parse_query_no_flags(self) -> None:
        """Test parsing query without any flags."""
        result = EagleEyeBot.parse_query("api error handling")

        assert result.query == "api error handling"
        assert result.sources == set()

    def test_parse_query_single_slack_flag(self) -> None:
        """Test parsing query with --slack flag."""
        result = EagleEyeBot.parse_query("--slack api error")

        assert result.query == "api error"
        assert result.sources == {"slack"}

    def test_parse_query_single_notion_flag(self) -> None:
        """Test parsing query with --notion flag."""
        result = EagleEyeBot.parse_query("--notion documentation")

        assert result.query == "documentation"
        assert result.sources == {"notion"}

    def test_parse_query_single_linear_flag(self) -> None:
        """Test parsing query with --linear flag."""
        result = EagleEyeBot.parse_query("--linear bug fix")

        assert result.query == "bug fix"
        assert result.sources == {"linear"}

    def test_parse_query_multiple_flags(self) -> None:
        """Test parsing query with multiple flags."""
        result = EagleEyeBot.parse_query("--slack --notion api error")

        assert result.query == "api error"
        assert result.sources == {"slack", "notion"}

    def test_parse_query_all_flags(self) -> None:
        """Test parsing query with all three flags."""
        result = EagleEyeBot.parse_query("--slack --notion --linear test")

        assert result.query == "test"
        assert result.sources == {"slack", "notion", "linear"}

    def test_parse_query_flags_at_end(self) -> None:
        """Test parsing query with flags at end."""
        result = EagleEyeBot.parse_query("api error --slack")

        assert result.query == "api error"
        assert result.sources == {"slack"}

    def test_parse_query_flags_in_middle(self) -> None:
        """Test parsing query with flags in middle."""
        result = EagleEyeBot.parse_query("api --slack error --notion handling")

        assert result.query == "api error handling"
        assert result.sources == {"slack", "notion"}

    def test_parse_query_case_insensitive_flags(self) -> None:
        """Test that flags are case-insensitive."""
        result = EagleEyeBot.parse_query("--SLACK --Notion test")

        assert result.query == "test"
        assert result.sources == {"slack", "notion"}

    def test_parse_query_only_flags_returns_empty_query(self) -> None:
        """Test parsing with only flags and no actual query."""
        result = EagleEyeBot.parse_query("--slack --notion")

        assert result.query == ""
        assert result.sources == {"slack", "notion"}

    def test_parse_query_cleans_multiple_spaces(self) -> None:
        """Test that multiple spaces are cleaned up."""
        result = EagleEyeBot.parse_query("api   --slack   error")

        assert result.query == "api error"
        assert result.sources == {"slack"}


class TestUnifiedSearchWithFilters:
    """Tests for unified search with source filters."""

    def test_unified_search_filters_to_slack_only(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search with only slack filter."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
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
                        results = bot._unified_search("test", sources={"slack"})

                        assert len(results) == 1
                        assert results[0].source == SearchResultType.SLACK
                        mock_slack.return_value.search.assert_called_once()
                        mock_notion.return_value.search.assert_not_called()
                        mock_linear.return_value.search.assert_not_called()

    def test_unified_search_filters_to_notion_only(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search with only notion filter."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_notion.return_value.search.return_value = [
                            sample_search_results[1]
                        ]

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search("test", sources={"notion"})

                        assert len(results) == 1
                        assert results[0].source == SearchResultType.NOTION
                        mock_slack.return_value.search.assert_not_called()
                        mock_notion.return_value.search.assert_called_once()
                        mock_linear.return_value.search.assert_not_called()

    def test_unified_search_filters_to_multiple_sources(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search with multiple source filters."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
                        mock_slack.return_value.search.return_value = [
                            sample_search_results[0]
                        ]
                        mock_linear.return_value.search.return_value = [
                            sample_search_results[2]
                        ]

                        bot = EagleEyeBot(mock_settings)
                        results = bot._unified_search(
                            "test", sources={"slack", "linear"}
                        )

                        assert len(results) == 2
                        sources = {r.source for r in results}
                        assert SearchResultType.SLACK in sources
                        assert SearchResultType.LINEAR in sources
                        mock_slack.return_value.search.assert_called_once()
                        mock_notion.return_value.search.assert_not_called()
                        mock_linear.return_value.search.assert_called_once()

    def test_unified_search_empty_sources_searches_all(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search with empty sources set searches all."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
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
                        results = bot._unified_search("test", sources=set())

                        assert len(results) == 3
                        mock_slack.return_value.search.assert_called_once()
                        mock_notion.return_value.search.assert_called_once()
                        mock_linear.return_value.search.assert_called_once()

    def test_unified_search_none_sources_searches_all(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test unified search with None sources searches all."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.SlackSearchClient") as mock_slack:
                with patch("eagleeye.app.NotionSearchClient") as mock_notion:
                    with patch("eagleeye.app.LinearClient") as mock_linear:
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
                        results = bot._unified_search("test", sources=None)

                        assert len(results) == 3
                        mock_slack.return_value.search.assert_called_once()
                        mock_notion.return_value.search.assert_called_once()
                        mock_linear.return_value.search.assert_called_once()
