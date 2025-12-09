"""Pytest configuration and fixtures."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from eagleeye.models.search import SearchResult, SearchResultType


@pytest.fixture
def mock_mcp_search_results() -> list[SearchResult]:
    """Sample search results from MCP servers."""
    return [
        SearchResult(
            source=SearchResultType.SLACK,
            title="#general",
            url="https://workspace.slack.com/archives/C123/p1234567890",
            snippet="This is a test message about the project",
            author="testuser",
            timestamp="1234567890",
        ),
        SearchResult(
            source=SearchResultType.NOTION,
            title="Test Page Title",
            url="https://notion.so/Test-Page-abc123def456",
            snippet="This is the page description",
        ),
        SearchResult(
            source=SearchResultType.LINEAR,
            title="[DEV-123] Fix authentication bug",
            url="https://linear.app/team/issue/DEV-123",
            snippet="Users are unable to login when using SSO",
            author="John Doe",
        ),
    ]


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Mock MCPSearchClient."""
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    mock.connect_all = AsyncMock()
    mock.disconnect_all = AsyncMock()
    return mock


@pytest.fixture
def mock_mcp_tool_result_slack() -> dict[str, Any]:
    """Sample MCP tool result for Slack search."""
    slack_data = [
        {
            "permalink": "https://workspace.slack.com/archives/C123/p123",
            "text": "Test message",
            "username": "testuser",
            "ts": "1234567890",
            "channel": {"name": "general"},
        }
    ]
    return {"content": [{"type": "text", "text": json.dumps(slack_data)}]}


@pytest.fixture
def mock_mcp_tool_result_notion() -> dict[str, Any]:
    """Sample MCP tool result for Notion search."""
    notion_data = [
        {
            "title": "Test Page",
            "url": "https://notion.so/page-123",
            "description": "Page description",
        }
    ]
    return {"content": [{"type": "text", "text": json.dumps(notion_data)}]}


@pytest.fixture
def mock_mcp_tool_result_linear() -> dict[str, Any]:
    """Sample MCP tool result for Linear search."""
    linear_data = [
        {
            "identifier": "DEV-123",
            "title": "Fix bug",
            "url": "https://linear.app/issue/DEV-123",
            "description": "Bug description",
            "assignee": {"name": "Developer"},
        }
    ]
    return {"content": [{"type": "text", "text": json.dumps(linear_data)}]}
