"""Tests for EagleEye Slack bot application (MCP-based)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eagleeye.app import EagleEyeBot, ParsedQuery
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
            with patch("eagleeye.app.MCPSearchClient"):
                bot = EagleEyeBot(mock_settings)

                mock_app_class.assert_called_once_with(
                    token="xoxb-test-token",
                    signing_secret="test-signing-secret",
                )
                assert bot.settings == mock_settings

    def test_init_creates_mcp_client(self, mock_settings: Settings) -> None:
        """Test that bot initializes MCP search client."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient") as mock_mcp:
                bot = EagleEyeBot(mock_settings)

                # MCPSearchClient should be called with a list of configs
                mock_mcp.assert_called_once()
                assert bot.mcp_client is not None


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


class TestAsyncSearch:
    """Tests for async search via MCP."""

    def test_run_async_search_calls_mcp_client(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that _run_async_search calls MCP client."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient") as mock_mcp_class:
                mock_client = MagicMock()
                mock_client.search = AsyncMock(return_value=sample_search_results)
                mock_mcp_class.return_value = mock_client

                bot = EagleEyeBot(mock_settings)
                results = bot._run_async_search("test query")

                assert len(results) == 3
                mock_client.search.assert_called_once()

    def test_run_async_search_passes_sources_filter(
        self, mock_settings: Settings
    ) -> None:
        """Test that sources filter is passed to MCP client."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient") as mock_mcp_class:
                mock_client = MagicMock()
                mock_client.search = AsyncMock(return_value=[])
                mock_mcp_class.return_value = mock_client

                bot = EagleEyeBot(mock_settings)
                bot._run_async_search("test", sources={"slack", "notion"})

                # Verify search was called with sources filter
                call_args = mock_client.search.call_args
                assert call_args.kwargs.get("sources") == {"slack", "notion"}

    def test_run_async_search_handles_error(self, mock_settings: Settings) -> None:
        """Test that search errors are handled gracefully."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient") as mock_mcp_class:
                mock_client = MagicMock()
                mock_client.search = AsyncMock(side_effect=Exception("MCP error"))
                mock_mcp_class.return_value = mock_client

                bot = EagleEyeBot(mock_settings)
                results = bot._run_async_search("test query")

                assert results == []


class TestFormatResults:
    """Tests for result formatting."""

    def test_format_results_creates_header(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that formatted results include header."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient"):
                bot = EagleEyeBot(mock_settings)
                blocks = bot._format_results_as_blocks(
                    "test query", sample_search_results
                )

                # First block should be header
                assert blocks[0]["type"] == "header"
                assert blocks[0]["text"]["text"] == "Search results for: test query"

    def test_format_results_groups_by_source(
        self, mock_settings: Settings, sample_search_results: list[SearchResult]
    ) -> None:
        """Test that results are grouped by source."""
        with patch("eagleeye.app.App"):
            with patch("eagleeye.app.MCPSearchClient"):
                bot = EagleEyeBot(mock_settings)
                blocks = bot._format_results_as_blocks("test", sample_search_results)

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
            with patch("eagleeye.app.MCPSearchClient"):
                bot = EagleEyeBot(mock_settings)
                blocks = bot._format_results_as_blocks("test", sample_search_results)

                divider_count = sum(1 for b in blocks if b["type"] == "divider")
                # At least one divider after header + one per source
                assert divider_count >= 2


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
            with patch("eagleeye.app.MCPSearchClient"):
                with patch("eagleeye.app.SocketModeHandler") as mock_handler:
                    bot = EagleEyeBot(mock_settings)
                    bot.start()

                    mock_handler.assert_called_once_with(bot.app, "xapp-test-token")
                    mock_handler.return_value.start.assert_called_once()


class TestParsedQuery:
    """Tests for ParsedQuery dataclass."""

    def test_parsed_query_with_sources(self) -> None:
        """Test ParsedQuery with sources."""
        pq = ParsedQuery(query="test query", sources={"slack", "notion"})

        assert pq.query == "test query"
        assert pq.sources == {"slack", "notion"}

    def test_parsed_query_empty_sources(self) -> None:
        """Test ParsedQuery with empty sources."""
        pq = ParsedQuery(query="test", sources=set())

        assert pq.query == "test"
        assert pq.sources == set()
