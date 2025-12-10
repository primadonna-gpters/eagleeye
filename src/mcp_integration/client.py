"""MCP client for connecting to and interacting with MCP servers."""

import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

from log_config import get_logger
from mcp_integration.servers import (
    SEARCH_TOOL_NAMES,
    MCPServerConfig,
    ServerType,
    get_search_tool_arguments,
)
from models.search import SearchResult, SearchResultType

logger = get_logger(__name__)

# Slack MCP tool names
SLACK_LIST_CHANNELS = "slack_list_channels"
SLACK_GET_CHANNEL_HISTORY = "slack_get_channel_history"


class MCPConnection:
    """A connection to a single MCP server."""

    def __init__(self, config: MCPServerConfig) -> None:
        """Initialize with server config."""
        self.config = config
        self.session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        self._exit_stack = AsyncExitStack()

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env if self.config.env else None,
        )

        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport

        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()

        logger.info(
            "mcp_server_connected",
            server_type=self.config.server_type.value,
        )

    async def disconnect(self) -> None:
        """Close the connection."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None

        logger.info(
            "mcp_server_disconnected",
            server_type=self.config.server_type.value,
        )

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        result: CallToolResult = await self.session.call_tool(tool_name, arguments)
        return result

    async def list_tools(self) -> list[str]:
        """List available tools on the server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        tools = await self.session.list_tools()
        return [tool.name for tool in tools.tools]


class MCPSearchClient:
    """Client for searching across multiple MCP servers."""

    def __init__(self, configs: list[MCPServerConfig]) -> None:
        """Initialize with server configurations."""
        self.configs = {config.server_type: config for config in configs}
        self.connections: dict[ServerType, MCPConnection] = {}
        self._connected = False

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers."""
        for server_type, config in self.configs.items():
            try:
                connection = MCPConnection(config)
                await connection.connect()
                self.connections[server_type] = connection

                # Log available tools for debugging
                tools = await connection.list_tools()
                logger.info(
                    "mcp_available_tools",
                    server_type=server_type.value,
                    tools=tools,
                )
            except Exception as e:
                logger.error(
                    "mcp_connection_failed",
                    server_type=server_type.value,
                    error=str(e),
                )
        self._connected = True

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for connection in self.connections.values():
            try:
                await connection.disconnect()
            except Exception as e:
                logger.error(
                    "mcp_disconnect_failed",
                    server_type=connection.config.server_type.value,
                    error=str(e),
                )
        self.connections.clear()
        self._connected = False

    async def search(
        self,
        query: str,
        sources: set[str] | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Search across specified sources.

        Args:
            query: Search query string
            sources: Set of source names to search (None = all)
            limit: Maximum results per source
        """
        if not self._connected:
            await self.connect_all()

        results: list[SearchResult] = []
        active_sources = sources if sources else {"slack", "notion", "linear"}

        # Create search tasks for each active source
        tasks: list[tuple[ServerType, asyncio.Task[list[SearchResult]]]] = []

        for source_name in active_sources:
            try:
                server_type = ServerType(source_name)
                if server_type in self.connections:
                    task = asyncio.create_task(
                        self._search_source(server_type, query, limit)
                    )
                    tasks.append((server_type, task))
            except ValueError:
                logger.warning("unknown_source", source=source_name)

        # Gather results
        for server_type, task in tasks:
            try:
                source_results = await task
                results.extend(source_results)
            except Exception as e:
                logger.error(
                    "search_failed",
                    source=server_type.value,
                    error=str(e),
                    query=query,
                )

        return results

    async def _search_source(
        self, server_type: ServerType, query: str, limit: int
    ) -> list[SearchResult]:
        """Search a single source."""
        connection = self.connections.get(server_type)
        if not connection or not connection.session:
            return []

        # Slack requires special handling since it doesn't have a search tool
        if server_type == ServerType.SLACK:
            return await self._search_slack(connection, query, limit)

        tool_name = SEARCH_TOOL_NAMES.get(server_type)
        if not tool_name:
            logger.warning("no_search_tool", server_type=server_type.value)
            return []

        arguments = get_search_tool_arguments(server_type, query, limit)

        try:
            result = await connection.call_tool(tool_name, arguments)
            return self._parse_results(server_type, result, query)
        except Exception as e:
            logger.error(
                "tool_call_failed",
                server_type=server_type.value,
                tool_name=tool_name,
                error=str(e),
            )
            return []

    async def _search_slack(
        self, connection: MCPConnection, query: str, limit: int
    ) -> list[SearchResult]:
        """Search Slack by fetching channel history and filtering.

        The official Slack MCP server doesn't have a search tool,
        so we list channels and fetch history, then filter client-side.
        """
        results: list[SearchResult] = []
        query_lower = query.lower()

        try:
            # Get list of channels
            channels_result = await connection.call_tool(
                SLACK_LIST_CHANNELS, {"limit": 10}
            )
            channels = self._parse_slack_channels(channels_result)

            # Fetch history from each channel and filter
            for channel in channels[:5]:  # Limit to 5 channels
                try:
                    history_result = await connection.call_tool(
                        SLACK_GET_CHANNEL_HISTORY,
                        {"channel_id": channel["id"], "limit": 20},
                    )
                    channel_results = self._parse_slack_history(
                        history_result, channel, query_lower
                    )
                    results.extend(channel_results)

                    if len(results) >= limit:
                        break
                except Exception as e:
                    logger.warning(
                        "slack_channel_history_failed",
                        channel_id=channel.get("id"),
                        error=str(e),
                    )

        except Exception as e:
            logger.error("slack_search_failed", error=str(e))

        return results[:limit]

    def _parse_slack_channels(self, result: CallToolResult) -> list[dict[str, Any]]:
        """Parse Slack channels from MCP result."""
        channels: list[dict[str, Any]] = []

        for content in result.content:
            if isinstance(content, TextContent):
                try:
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        channels.extend(data)
                    elif isinstance(data, dict):
                        channels.extend(data.get("channels", []))
                except json.JSONDecodeError:
                    pass

        return channels

    def _parse_slack_history(
        self,
        result: CallToolResult,
        channel: dict[str, Any],
        query_lower: str,
    ) -> list[SearchResult]:
        """Parse Slack history and filter by query."""
        results: list[SearchResult] = []
        channel_name = channel.get("name", "unknown")

        for content in result.content:
            if isinstance(content, TextContent):
                try:
                    data = json.loads(content.text)
                    messages = (
                        data if isinstance(data, list) else data.get("messages", [])
                    )

                    for msg in messages:
                        text = msg.get("text", "")
                        if query_lower in text.lower():
                            results.append(
                                SearchResult(
                                    source=SearchResultType.SLACK,
                                    title=f"#{channel_name}",
                                    url=msg.get("permalink", ""),
                                    snippet=text[:200],
                                    author=msg.get("user"),
                                    timestamp=msg.get("ts"),
                                )
                            )
                except json.JSONDecodeError:
                    pass

        return results

    def _parse_results(
        self,
        server_type: ServerType,
        result: CallToolResult,
        query: str = "",
    ) -> list[SearchResult]:
        """Parse MCP tool results into SearchResult objects."""
        results: list[SearchResult] = []
        result_type = _server_type_to_result_type(server_type)

        for content in result.content:
            if isinstance(content, TextContent):
                try:
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        for item in data:
                            parsed = self._parse_item(result_type, item)
                            if parsed:
                                results.append(parsed)
                    elif isinstance(data, dict):
                        # Handle nested results
                        items_data = data.get("results") or data.get("items") or [data]
                        for item in items_data:
                            parsed = self._parse_item(result_type, item)
                            if parsed:
                                results.append(parsed)
                except json.JSONDecodeError:
                    # Plain text result
                    results.append(
                        SearchResult(
                            source=result_type,
                            title="Search Result",
                            url="",
                            snippet=content.text[:200],
                        )
                    )

        return results

    def _parse_item(
        self, result_type: SearchResultType, item: dict[str, Any]
    ) -> SearchResult | None:
        """Parse a single result item."""
        try:
            title = item.get("title", item.get("name", "Untitled"))
            url = item.get("url", item.get("permalink", item.get("link", "")))
            raw_snippet = item.get(
                "snippet",
                item.get("description", item.get("text", item.get("content", ""))),
            )
            snippet = str(raw_snippet)[:200] if raw_snippet else ""
            author = item.get("author", item.get("user", item.get("assignee")))
            if isinstance(author, dict):
                author = author.get("name", author.get("username", str(author)))

            timestamp = item.get("timestamp", item.get("created_at", item.get("ts")))

            return SearchResult(
                source=result_type,
                title=str(title),
                url=str(url),
                snippet=snippet,
                author=str(author) if author else None,
                timestamp=str(timestamp) if timestamp else None,
            )
        except Exception as e:
            logger.error("parse_item_failed", error=str(e), item=str(item)[:100])
            return None


def _server_type_to_result_type(server_type: ServerType) -> SearchResultType:
    """Convert ServerType to SearchResultType."""
    return SearchResultType(server_type.value)
