"""Tests for search result models."""

from models.search import SearchResult, SearchResultType


class TestSearchResultType:
    """Tests for SearchResultType enum."""

    def test_enum_values(self) -> None:
        """Test enum values are correct."""
        assert SearchResultType.SLACK.value == "slack"
        assert SearchResultType.NOTION.value == "notion"
        assert SearchResultType.LINEAR.value == "linear"


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self) -> None:
        """Test creating a SearchResult."""
        result = SearchResult(
            source=SearchResultType.SLACK,
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
        )

        assert result.source == SearchResultType.SLACK
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.timestamp is None
        assert result.author is None
        assert result.extra is None

    def test_create_search_result_with_optional_fields(self) -> None:
        """Test creating a SearchResult with optional fields."""
        result = SearchResult(
            source=SearchResultType.LINEAR,
            title="Issue Title",
            url="https://linear.app/issue/123",
            snippet="Issue description",
            timestamp="1234567890",
            author="John Doe",
            extra={"status": "In Progress"},
        )

        assert result.timestamp == "1234567890"
        assert result.author == "John Doe"
        assert result.extra == {"status": "In Progress"}

    def test_to_slack_block_slack_source(self) -> None:
        """Test to_slack_block with Slack source."""
        result = SearchResult(
            source=SearchResultType.SLACK,
            title="#general",
            url="https://slack.com/message/123",
            snippet="Hello world",
            author="testuser",
            timestamp="1234567890",
        )

        block = result.to_slack_block()

        assert block["type"] == "section"
        assert block["text"]["type"] == "mrkdwn"
        text = block["text"]["text"]
        assert ":slack:" in text
        assert "*<https://slack.com/message/123|#general>*" in text
        assert "Hello world" in text
        assert "_by testuser_" in text

    def test_to_slack_block_notion_source(self) -> None:
        """Test to_slack_block with Notion source."""
        result = SearchResult(
            source=SearchResultType.NOTION,
            title="My Page",
            url="https://notion.so/page/123",
            snippet="Page content",
        )

        block = result.to_slack_block()
        text = block["text"]["text"]

        assert ":notion:" in text
        assert "*<https://notion.so/page/123|My Page>*" in text

    def test_to_slack_block_linear_source(self) -> None:
        """Test to_slack_block with Linear source."""
        result = SearchResult(
            source=SearchResultType.LINEAR,
            title="[DEV-123] Bug fix",
            url="https://linear.app/issue/DEV-123",
            snippet="Fix the bug",
        )

        block = result.to_slack_block()
        text = block["text"]["text"]

        assert ":linear:" in text
        assert "*<https://linear.app/issue/DEV-123|[DEV-123] Bug fix>*" in text

    def test_to_slack_block_without_optional_fields(self) -> None:
        """Test to_slack_block without optional fields."""
        result = SearchResult(
            source=SearchResultType.SLACK,
            title="Channel",
            url="https://example.com",
            snippet="",
        )

        block = result.to_slack_block()
        text = block["text"]["text"]

        # Should not contain author or timestamp formatting
        assert "_by" not in text
        assert "<!date^" not in text

    def test_to_slack_block_truncates_long_snippet(self) -> None:
        """Test that to_slack_block truncates long snippets."""
        long_snippet = "x" * 300
        result = SearchResult(
            source=SearchResultType.SLACK,
            title="Channel",
            url="https://example.com",
            snippet=long_snippet,
        )

        block = result.to_slack_block()
        text = block["text"]["text"]

        # Snippet should be truncated to 200 chars
        assert "x" * 200 in text
        assert "x" * 201 not in text
