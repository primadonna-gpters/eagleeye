"""MCP server configuration and types."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ServerType(str, Enum):
    """Type of MCP server."""

    SLACK = "slack"
    NOTION = "notion"
    LINEAR = "linear"


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""

    server_type: ServerType
    command: str
    args: list[str] = []
    env: dict[str, str] = {}

    @classmethod
    def slack(cls, bot_token: str) -> "MCPServerConfig":
        """Create Slack MCP server config.

        Uses @anthropic/mcp-server-slack (npx).
        """
        return cls(
            server_type=ServerType.SLACK,
            command="npx",
            args=["-y", "@anthropic-ai/mcp-server-slack"],
            env={"SLACK_BOT_TOKEN": bot_token},
        )

    @classmethod
    def notion(cls, api_key: str) -> "MCPServerConfig":
        """Create Notion MCP server config.

        Uses @notionhq/notion-mcp-server (npx).
        """
        return cls(
            server_type=ServerType.NOTION,
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={"NOTION_API_KEY": api_key},
        )

    @classmethod
    def linear(cls, api_key: str) -> "MCPServerConfig":
        """Create Linear MCP server config.

        Uses @linear/mcp-server (npx).
        """
        return cls(
            server_type=ServerType.LINEAR,
            command="npx",
            args=["-y", "mcp-server-linear"],
            env={"LINEAR_API_KEY": api_key},
        )


# Tool name mappings for search operations
SEARCH_TOOL_NAMES: dict[ServerType, str] = {
    ServerType.SLACK: "search_messages",
    ServerType.NOTION: "notion_search",
    ServerType.LINEAR: "search_issues",
}


def get_search_tool_arguments(
    server_type: ServerType, query: str, limit: int = 5
) -> dict[str, Any]:
    """Get the arguments for a search tool call."""
    if server_type == ServerType.SLACK:
        return {"query": query, "count": limit}
    elif server_type == ServerType.NOTION:
        return {"query": query, "page_size": limit}
    elif server_type == ServerType.LINEAR:
        return {"query": query, "first": limit}
    return {"query": query}
