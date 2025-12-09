"""Tests for Linear search integration."""

from typing import Any
from unittest.mock import MagicMock

from eagleeye.integrations.linear import LinearClient
from eagleeye.models.search import SearchResultType


class TestLinearClient:
    """Tests for LinearClient."""

    def test_search_returns_results(
        self,
        mock_httpx_client: MagicMock,
        mock_linear_response: dict[str, Any],
    ) -> None:
        """Test that search returns SearchResult objects."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_linear_response
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("authentication")

        assert len(results) == 2
        assert results[0].source == SearchResultType.LINEAR
        assert results[0].title == "[DEV-123] Fix authentication bug"
        assert "unable to login" in results[0].snippet
        assert results[0].author == "John Doe"
        assert results[0].extra == {"status": "In Progress"}

    def test_search_handles_issue_without_assignee(
        self,
        mock_httpx_client: MagicMock,
        mock_linear_response: dict[str, Any],
    ) -> None:
        """Test that search handles issues without assignee."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_linear_response
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("search feature")

        # Second result has no assignee
        assert results[1].author is None

    def test_search_handles_null_description(
        self,
        mock_httpx_client: MagicMock,
        mock_linear_response: dict[str, Any],
    ) -> None:
        """Test that search handles null description."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_linear_response
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("search feature")

        # Second result has null description
        assert results[1].snippet == ""

    def test_search_respects_limit(
        self,
        mock_httpx_client: MagicMock,
        mock_linear_response: dict[str, Any],
    ) -> None:
        """Test that search respects the limit parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_linear_response
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("test", limit=1)

        assert len(results) == 1

    def test_search_handles_empty_response(
        self,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Test that search handles empty response gracefully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"searchIssues": {"nodes": []}}}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("nonexistent")

        assert results == []

    def test_search_handles_api_error(
        self,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Test that search handles API errors gracefully."""
        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = Exception("API Error")
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        results = client.search("test")

        assert results == []

    def test_client_sets_correct_headers(
        self,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Test that client sets correct authorization headers."""
        api_key = "lin_api_test_key"
        client = LinearClient(api_key=api_key)

        assert client.headers["Authorization"] == api_key
        assert client.headers["Content-Type"] == "application/json"

    def test_search_sends_correct_graphql_query(
        self,
        mock_httpx_client: MagicMock,
    ) -> None:
        """Test that search sends correct GraphQL query."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"searchIssues": {"nodes": []}}}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.return_value = mock_client_instance

        client = LinearClient(api_key="lin_api_test")
        client.search("test query", limit=10)

        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        json_payload = call_args.kwargs["json"]

        assert "query" in json_payload
        assert json_payload["variables"]["query"] == "test query"
        assert json_payload["variables"]["first"] == 10
