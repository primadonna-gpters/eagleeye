"""Tests for Slack search integration."""

from typing import Any
from unittest.mock import MagicMock

from eagleeye.integrations.slack_search import SlackSearchClient
from eagleeye.models.search import SearchResultType


class TestSlackSearchClient:
    """Tests for SlackSearchClient."""

    def test_search_returns_results(
        self,
        mock_slack_client: MagicMock,
        mock_slack_response: dict[str, Any],
    ) -> None:
        """Test that search returns SearchResult objects."""
        mock_instance = MagicMock()
        mock_instance.search_messages.return_value = mock_slack_response
        mock_slack_client.return_value = mock_instance

        client = SlackSearchClient(token="xoxb-test-token")
        results = client.search("test query")

        assert len(results) == 2
        assert results[0].source == SearchResultType.SLACK
        assert results[0].title == "#general"
        assert "test message" in results[0].snippet
        assert results[0].author == "testuser"
        assert results[0].timestamp == "1234567890"

    def test_search_respects_limit(
        self,
        mock_slack_client: MagicMock,
        mock_slack_response: dict[str, Any],
    ) -> None:
        """Test that search respects the limit parameter."""
        mock_instance = MagicMock()
        mock_instance.search_messages.return_value = mock_slack_response
        mock_slack_client.return_value = mock_instance

        client = SlackSearchClient(token="xoxb-test-token")
        results = client.search("test query", limit=1)

        assert len(results) == 1

    def test_search_handles_empty_response(
        self,
        mock_slack_client: MagicMock,
    ) -> None:
        """Test that search handles empty response gracefully."""
        mock_instance = MagicMock()
        mock_instance.search_messages.return_value = {"ok": True, "messages": {}}
        mock_slack_client.return_value = mock_instance

        client = SlackSearchClient(token="xoxb-test-token")
        results = client.search("test query")

        assert results == []

    def test_search_handles_api_error(
        self,
        mock_slack_client: MagicMock,
    ) -> None:
        """Test that search handles API errors gracefully."""
        mock_instance = MagicMock()
        mock_instance.search_messages.side_effect = Exception("API Error")
        mock_slack_client.return_value = mock_instance

        client = SlackSearchClient(token="xoxb-test-token")
        results = client.search("test query")

        assert results == []

    def test_search_handles_missing_fields(
        self,
        mock_slack_client: MagicMock,
    ) -> None:
        """Test that search handles messages with missing fields."""
        mock_instance = MagicMock()
        mock_instance.search_messages.return_value = {
            "ok": True,
            "messages": {
                "matches": [
                    {
                        "text": "Message with minimal fields",
                    }
                ]
            },
        }
        mock_slack_client.return_value = mock_instance

        client = SlackSearchClient(token="xoxb-test-token")
        results = client.search("test query")

        assert len(results) == 1
        assert results[0].source == SearchResultType.SLACK
        assert results[0].url == ""
        assert results[0].author == "unknown"
        assert results[0].timestamp is None
