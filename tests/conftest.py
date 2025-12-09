"""Pytest configuration and fixtures."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_slack_response() -> dict[str, Any]:
    """Sample Slack search_messages response."""
    return {
        "ok": True,
        "messages": {
            "matches": [
                {
                    "permalink": "https://workspace.slack.com/archives/C123/p1234567890",
                    "text": "This is a test message about the project",
                    "username": "testuser",
                    "ts": "1234567890.123456",
                    "channel": {"name": "general"},
                },
                {
                    "permalink": "https://workspace.slack.com/archives/C456/p1234567891",
                    "text": "Another message with search keyword",
                    "username": "anotheruser",
                    "ts": "1234567891.654321",
                    "channel": {"name": "random"},
                },
            ]
        },
    }


@pytest.fixture
def mock_notion_response() -> dict[str, Any]:
    """Sample Notion search response."""
    return {
        "results": [
            {
                "object": "page",
                "id": "abc123-def456",
                "url": "https://notion.so/Test-Page-abc123def456",
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Test Page Title"}],
                    },
                    "Description": {
                        "type": "rich_text",
                        "rich_text": [{"plain_text": "This is the page description"}],
                    },
                },
            },
            {
                "object": "database",
                "id": "xyz789",
                "url": "https://notion.so/Test-Database-xyz789",
                "title": [{"plain_text": "Test Database"}],
                "properties": {},
            },
        ]
    }


@pytest.fixture
def mock_linear_response() -> dict[str, Any]:
    """Sample Linear GraphQL response."""
    return {
        "data": {
            "searchIssues": {
                "nodes": [
                    {
                        "id": "issue-1",
                        "identifier": "DEV-123",
                        "title": "Fix authentication bug",
                        "description": "Users are unable to login when using SSO",
                        "url": "https://linear.app/team/issue/DEV-123",
                        "state": {"name": "In Progress"},
                        "assignee": {"name": "John Doe"},
                        "createdAt": "2024-01-15T10:00:00Z",
                    },
                    {
                        "id": "issue-2",
                        "identifier": "DEV-456",
                        "title": "Add search feature",
                        "description": None,
                        "url": "https://linear.app/team/issue/DEV-456",
                        "state": {"name": "Todo"},
                        "assignee": None,
                        "createdAt": "2024-01-16T11:00:00Z",
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_slack_client() -> Generator[MagicMock, None, None]:
    """Mock Slack WebClient."""
    with patch("eagleeye.integrations.slack_search.WebClient") as mock:
        yield mock


@pytest.fixture
def mock_notion_client() -> Generator[MagicMock, None, None]:
    """Mock Notion Client."""
    with patch("eagleeye.integrations.notion.Client") as mock:
        yield mock


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Mock httpx Client for Linear."""
    with patch("eagleeye.integrations.linear.httpx.Client") as mock:
        yield mock
