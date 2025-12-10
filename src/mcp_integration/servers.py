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
    def slack(cls, bot_token: str, team_id: str = "") -> "MCPServerConfig":
        """Create Slack MCP server config.

        Uses @modelcontextprotocol/server-slack (official).
        Note: This server does not have a search_messages tool.
        We use slack_list_channels + slack_get_channel_history
        with client-side filtering.
        See: https://www.npmjs.com/package/@modelcontextprotocol/server-slack
        """
        env = {"SLACK_BOT_TOKEN": bot_token}
        if team_id:
            env["SLACK_TEAM_ID"] = team_id
        return cls(
            server_type=ServerType.SLACK,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-slack"],
            env=env,
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
            env={"NOTION_TOKEN": api_key},
        )

    @classmethod
    def linear(cls, api_key: str) -> "MCPServerConfig":
        """Create Linear MCP server config.

        Uses @tacticlaunch/mcp-linear which is actively maintained.
        The original linear-mcp-server is deprecated.
        See: https://www.npmjs.com/package/@tacticlaunch/mcp-linear
        """
        return cls(
            server_type=ServerType.LINEAR,
            command="npx",
            args=["-y", "@tacticlaunch/mcp-linear"],
            env={"LINEAR_API_KEY": api_key},
        )


# Tool name mappings for search operations
# Note: Slack uses channel history (no search tool in official package)
SEARCH_TOOL_NAMES: dict[ServerType, str] = {
    ServerType.SLACK: "slack_get_channel_history",  # @modelcontextprotocol/server-slack
    ServerType.NOTION: "API-post-search",  # @notionhq/notion-mcp-server
    ServerType.LINEAR: "linear_searchIssues",  # @tacticlaunch/mcp-linear
}


def get_search_tool_arguments(
    server_type: ServerType,
    query: str,
    limit: int = 5,
    channel_id: str = "",
) -> dict[str, Any]:
    """Get the arguments for a search tool call.

    Args:
        server_type: Type of MCP server.
        query: Search query string.
        limit: Maximum number of results.
        channel_id: For Slack, the channel ID to get history from.
    """
    if server_type == ServerType.SLACK:
        # Slack uses channel history - query is used for client-side filtering
        args: dict[str, Any] = {"limit": limit}
        if channel_id:
            args["channel_id"] = channel_id
        return args
    elif server_type == ServerType.NOTION:
        # Notion API search endpoint parameters
        return {
            "query": query,
            "page_size": limit,
            "filter": {"property": "object", "value": "page"},
        }
    elif server_type == ServerType.LINEAR:
        # @tacticlaunch/mcp-linear search_issues
        return {"query": query, "limit": limit}
    return {"query": query}
