"""Tests for Notion search integration."""

from typing import Any
from unittest.mock import MagicMock

from eagleeye.integrations.notion import NotionSearchClient
from eagleeye.models.search import SearchResultType


class TestNotionSearchClient:
    """Tests for NotionSearchClient."""

    def test_search_returns_results(
        self,
        mock_notion_client: MagicMock,
        mock_notion_response: dict[str, Any],
    ) -> None:
        """Test that search returns SearchResult objects."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = mock_notion_response
        mock_notion_client.return_value = mock_instance

        client = NotionSearchClient(api_key="test-api-key")
        results = client.search("test query")

        assert len(results) == 2
        assert results[0].source == SearchResultType.NOTION
        assert results[0].title == "Test Page Title"
        assert results[0].snippet == "This is the page description"
        assert results[0].extra == {"type": "page"}

    def test_search_respects_limit(
        self,
        mock_notion_client: MagicMock,
        mock_notion_response: dict[str, Any],
    ) -> None:
        """Test that search respects the limit parameter."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = mock_notion_response
        mock_notion_client.return_value = mock_instance

        client = NotionSearchClient(api_key="test-api-key")
        results = client.search("test query", limit=1)

        assert len(results) == 1

    def test_search_handles_empty_response(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test that search handles empty response gracefully."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = {"results": []}
        mock_notion_client.return_value = mock_instance

        client = NotionSearchClient(api_key="test-api-key")
        results = client.search("test query")

        assert results == []

    def test_search_handles_api_error(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test that search handles API errors gracefully."""
        mock_instance = MagicMock()
        mock_instance.search.side_effect = Exception("API Error")
        mock_notion_client.return_value = mock_instance

        client = NotionSearchClient(api_key="test-api-key")
        results = client.search("test query")

        assert results == []

    def test_extract_title_from_title_property(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test title extraction from title property."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "My Title"}],
                }
            }
        }
        assert client._extract_title(item) == "My Title"

    def test_extract_title_from_name_property(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test title extraction from Name property."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "My Name"}],
                }
            }
        }
        assert client._extract_title(item) == "My Name"

    def test_extract_title_fallback(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test title extraction fallback for database."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {"title": [{"plain_text": "Database Title"}], "properties": {}}
        assert client._extract_title(item) == "Database Title"

    def test_extract_title_returns_empty_when_missing(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test title extraction returns empty string when missing."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {"properties": {}}
        assert client._extract_title(item) == ""

    def test_extract_snippet_from_description(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test snippet extraction from Description property."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {
            "properties": {
                "Description": {
                    "type": "rich_text",
                    "rich_text": [{"plain_text": "This is the description"}],
                }
            }
        }
        assert client._extract_snippet(item) == "This is the description"

    def test_extract_snippet_returns_empty_when_missing(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test snippet extraction returns empty string when missing."""
        mock_notion_client.return_value = MagicMock()

        client = NotionSearchClient(api_key="test-api-key")

        item = {"properties": {}}
        assert client._extract_snippet(item) == ""

    def test_search_handles_untitled_page(
        self,
        mock_notion_client: MagicMock,
    ) -> None:
        """Test that search handles pages without title."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = {
            "results": [
                {
                    "object": "page",
                    "id": "abc123",
                    "properties": {},
                }
            ]
        }
        mock_notion_client.return_value = mock_instance

        client = NotionSearchClient(api_key="test-api-key")
        results = client.search("test query")

        assert len(results) == 1
        assert results[0].title == "Untitled"
