"""Tests for Slack message formatting utilities."""

from slack_formatter import (
    create_context_block,
    create_divider_block,
    create_header_block,
    create_section_block,
    format_error_response,
    format_help_response,
    format_search_loading,
    format_search_response,
)


class TestBlockCreation:
    """Tests for individual block creation functions."""

    def test_create_header_block(self) -> None:
        """Test header block creation."""
        block = create_header_block("Test Header", ":mag:")

        assert block["type"] == "header"
        assert block["text"]["type"] == "plain_text"
        assert block["text"]["text"] == ":mag: Test Header"
        assert block["text"]["emoji"] is True

    def test_create_section_block(self) -> None:
        """Test section block creation."""
        block = create_section_block("*Bold* and _italic_")

        assert block["type"] == "section"
        assert block["text"]["type"] == "mrkdwn"
        assert block["text"]["text"] == "*Bold* and _italic_"

    def test_create_context_block(self) -> None:
        """Test context block creation."""
        block = create_context_block(["_meta1_", "_meta2_"])

        assert block["type"] == "context"
        assert len(block["elements"]) == 2
        assert block["elements"][0]["type"] == "mrkdwn"
        assert block["elements"][0]["text"] == "_meta1_"

    def test_create_divider_block(self) -> None:
        """Test divider block creation."""
        block = create_divider_block()

        assert block["type"] == "divider"


class TestSearchLoading:
    """Tests for search loading message formatting."""

    def test_format_search_loading(self) -> None:
        """Test loading message includes query."""
        result = format_search_loading("test query")

        assert "text" in result  # Fallback text for notifications
        assert "blocks" in result
        assert len(result["blocks"]) == 2
        assert "*test query*" in result["blocks"][0]["text"]["text"]
        assert "_검색 중..._" in result["blocks"][1]["elements"][0]["text"]


class TestSearchResponse:
    """Tests for search response formatting."""

    def test_format_search_response_basic(self) -> None:
        """Test basic response formatting."""
        text = ":mag: *검색 결과*\n\nFound 3 results"
        result = format_search_response(text)

        assert "text" in result  # Fallback text
        assert "blocks" in result
        assert len(result["blocks"]) >= 1

    def test_format_search_response_with_divider(self) -> None:
        """Test response with horizontal rule creates divider."""
        text = "Results above\n---\nSummary below"
        result = format_search_response(text)

        # Should have 3 blocks: section, divider, section
        assert len(result["blocks"]) == 3
        assert result["blocks"][1]["type"] == "divider"

    def test_format_search_response_multiline(self) -> None:
        """Test multiline response preserves formatting."""
        text = ":slack: *Slack*\n• Item 1\n• Item 2"
        result = format_search_response(text)

        assert "text" in result
        assert "blocks" in result
        assert "• Item 1" in result["blocks"][0]["text"]["text"]


class TestErrorResponse:
    """Tests for error response formatting."""

    def test_format_error_response(self) -> None:
        """Test error message formatting."""
        result = format_error_response("Connection failed")

        assert "text" in result
        assert "blocks" in result
        assert len(result["blocks"]) == 3
        assert ":x:" in result["blocks"][0]["text"]["text"]
        assert "```Connection failed```" in result["blocks"][1]["text"]["text"]
        assert "다시 시도" in result["blocks"][2]["elements"][0]["text"]


class TestHelpResponse:
    """Tests for help response formatting."""

    def test_format_help_response(self) -> None:
        """Test help message contains usage info."""
        result = format_help_response()

        assert "text" in result
        assert "blocks" in result
        assert len(result["blocks"]) >= 4

        # Check that help contains key information
        all_text = " ".join(
            block.get("text", {}).get("text", "")
            for block in result["blocks"]
            if block.get("type") == "section"
        )
        assert "EagleEye" in all_text
        assert "@EagleEye" in all_text
