"""Tests for MCP client and server configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eagleeye.mcp.client import (
    MCPConnection,
    MCPSearchClient,
    _server_type_to_result_type,
)
from eagleeye.mcp.servers import (
    SEARCH_TOOL_NAMES,
    MCPServerConfig,
    ServerType,
    get_search_tool_arguments,
)
from eagleeye.models.search import SearchResultType


class TestMCPServerConfig:
    """Tests for MCP server configuration."""

    def test_slack_config(self) -> None:
        """Test Slack MCP server config creation."""
        config = MCPServerConfig.slack("xoxb-test-token")

        assert config.server_type == ServerType.SLACK
        assert config.command == "npx"
        assert "@anthropic-ai/mcp-server-slack" in config.args
        assert config.env["SLACK_BOT_TOKEN"] == "xoxb-test-token"

    def test_notion_config(self) -> None:
        """Test Notion MCP server config creation."""
        config = MCPServerConfig.notion("secret_notion_key")

        assert config.server_type == ServerType.NOTION
        assert config.command == "npx"
        assert "@notionhq/notion-mcp-server" in config.args
        assert config.env["NOTION_API_KEY"] == "secret_notion_key"

    def test_linear_config(self) -> None:
        """Test Linear MCP server config creation."""
        config = MCPServerConfig.linear("lin_api_key")

        assert config.server_type == ServerType.LINEAR
        assert config.command == "npx"
        assert "mcp-server-linear" in config.args
        assert config.env["LINEAR_API_KEY"] == "lin_api_key"

    def test_custom_config(self) -> None:
        """Test custom MCP server config."""
        config = MCPServerConfig(
            server_type=ServerType.SLACK,
            command="python",
            args=["custom_server.py"],
            env={"CUSTOM_VAR": "value"},
        )

        assert config.command == "python"
        assert config.args == ["custom_server.py"]
        assert config.env["CUSTOM_VAR"] == "value"


class TestServerType:
    """Tests for ServerType enum."""

    def test_server_type_values(self) -> None:
        """Test ServerType enum values."""
        assert ServerType.SLACK.value == "slack"
        assert ServerType.NOTION.value == "notion"
        assert ServerType.LINEAR.value == "linear"

    def test_server_type_from_string(self) -> None:
        """Test creating ServerType from string."""
        assert ServerType("slack") == ServerType.SLACK
        assert ServerType("notion") == ServerType.NOTION
        assert ServerType("linear") == ServerType.LINEAR


class TestSearchToolNames:
    """Tests for search tool name mappings."""

    def test_slack_tool_name(self) -> None:
        """Test Slack search tool name."""
        assert SEARCH_TOOL_NAMES[ServerType.SLACK] == "search_messages"

    def test_notion_tool_name(self) -> None:
        """Test Notion search tool name."""
        assert SEARCH_TOOL_NAMES[ServerType.NOTION] == "notion_search"

    def test_linear_tool_name(self) -> None:
        """Test Linear search tool name."""
        assert SEARCH_TOOL_NAMES[ServerType.LINEAR] == "search_issues"


class TestGetSearchToolArguments:
    """Tests for search tool arguments."""

    def test_slack_arguments(self) -> None:
        """Test Slack search arguments."""
        args = get_search_tool_arguments(ServerType.SLACK, "test query", limit=10)

        assert args["query"] == "test query"
        assert args["count"] == 10

    def test_notion_arguments(self) -> None:
        """Test Notion search arguments."""
        args = get_search_tool_arguments(ServerType.NOTION, "test query", limit=5)

        assert args["query"] == "test query"
        assert args["page_size"] == 5

    def test_linear_arguments(self) -> None:
        """Test Linear search arguments."""
        args = get_search_tool_arguments(ServerType.LINEAR, "test query", limit=3)

        assert args["query"] == "test query"
        assert args["first"] == 3


class TestServerTypeToResultType:
    """Tests for ServerType to SearchResultType conversion."""

    def test_slack_conversion(self) -> None:
        """Test Slack type conversion."""
        result = _server_type_to_result_type(ServerType.SLACK)
        assert result == SearchResultType.SLACK

    def test_notion_conversion(self) -> None:
        """Test Notion type conversion."""
        result = _server_type_to_result_type(ServerType.NOTION)
        assert result == SearchResultType.NOTION

    def test_linear_conversion(self) -> None:
        """Test Linear type conversion."""
        result = _server_type_to_result_type(ServerType.LINEAR)
        assert result == SearchResultType.LINEAR


class TestMCPConnection:
    """Tests for MCP connection."""

    def test_init(self) -> None:
        """Test MCPConnection initialization."""
        config = MCPServerConfig.slack("token")
        connection = MCPConnection(config)

        assert connection.config == config
        assert connection.session is None

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test establishing connection."""
        config = MCPServerConfig.slack("token")
        connection = MCPConnection(config)

        with patch("eagleeye.mcp.client.stdio_client") as mock_stdio:
            with patch("eagleeye.mcp.client.ClientSession") as mock_session_class:
                mock_stdio.return_value.__aenter__ = AsyncMock(
                    return_value=(MagicMock(), MagicMock())
                )
                mock_stdio.return_value.__aexit__ = AsyncMock()

                mock_session = MagicMock()
                mock_session.initialize = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                await connection.connect()

                assert connection.session is not None

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test closing connection."""
        config = MCPServerConfig.slack("token")
        connection = MCPConnection(config)
        connection._exit_stack = MagicMock()
        connection._exit_stack.aclose = AsyncMock()

        await connection.disconnect()

        assert connection.session is None
        assert connection._exit_stack is None


class TestMCPSearchClient:
    """Tests for MCP search client."""

    def test_init_with_configs(self) -> None:
        """Test MCPSearchClient initialization."""
        configs = [
            MCPServerConfig.slack("slack-token"),
            MCPServerConfig.notion("notion-key"),
        ]
        client = MCPSearchClient(configs)

        assert ServerType.SLACK in client.configs
        assert ServerType.NOTION in client.configs
        assert ServerType.LINEAR not in client.configs

    @pytest.mark.asyncio
    async def test_connect_all(self) -> None:
        """Test connecting to all servers."""
        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        with patch.object(MCPConnection, "connect", new_callable=AsyncMock):
            await client.connect_all()

            assert client._connected is True
            assert ServerType.SLACK in client.connections

    @pytest.mark.asyncio
    async def test_disconnect_all(self) -> None:
        """Test disconnecting from all servers."""
        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        mock_connection = MagicMock()
        mock_connection.disconnect = AsyncMock()
        mock_connection.config = configs[0]
        client.connections[ServerType.SLACK] = mock_connection
        client._connected = True

        await client.disconnect_all()

        mock_connection.disconnect.assert_called_once()
        assert client._connected is False
        assert len(client.connections) == 0

    @pytest.mark.asyncio
    async def test_search_calls_correct_sources(self) -> None:
        """Test that search calls correct sources based on filter."""
        configs = [
            MCPServerConfig.slack("slack-token"),
            MCPServerConfig.notion("notion-key"),
            MCPServerConfig.linear("linear-key"),
        ]
        client = MCPSearchClient(configs)

        # Setup mock connections
        for server_type in [ServerType.SLACK, ServerType.NOTION, ServerType.LINEAR]:
            mock_connection = MagicMock()
            mock_connection.session = MagicMock()
            mock_connection.call_tool = AsyncMock(return_value=MagicMock(content=[]))
            client.connections[server_type] = mock_connection

        client._connected = True

        # Search only Slack
        await client.search("test", sources={"slack"})

        client.connections[ServerType.SLACK].call_tool.assert_called()
        client.connections[ServerType.NOTION].call_tool.assert_not_called()
        client.connections[ServerType.LINEAR].call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_all_sources_when_none_specified(self) -> None:
        """Test that search calls all sources when none specified."""
        configs = [
            MCPServerConfig.slack("slack-token"),
            MCPServerConfig.notion("notion-key"),
            MCPServerConfig.linear("linear-key"),
        ]
        client = MCPSearchClient(configs)

        # Setup mock connections
        for server_type in [ServerType.SLACK, ServerType.NOTION, ServerType.LINEAR]:
            mock_connection = MagicMock()
            mock_connection.session = MagicMock()
            mock_connection.call_tool = AsyncMock(return_value=MagicMock(content=[]))
            client.connections[server_type] = mock_connection

        client._connected = True

        # Search all sources
        await client.search("test", sources=None)

        client.connections[ServerType.SLACK].call_tool.assert_called()
        client.connections[ServerType.NOTION].call_tool.assert_called()
        client.connections[ServerType.LINEAR].call_tool.assert_called()


class TestMCPResultParsing:
    """Tests for MCP result parsing."""

    def test_parse_item_with_full_data(self) -> None:
        """Test parsing an item with all fields."""
        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        item = {
            "title": "Test Title",
            "url": "https://example.com",
            "snippet": "Test snippet",
            "author": "testuser",
            "timestamp": "1234567890",
        }

        result = client._parse_item(SearchResultType.SLACK, item)

        assert result is not None
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.author == "testuser"
        assert result.timestamp == "1234567890"

    def test_parse_item_with_minimal_data(self) -> None:
        """Test parsing an item with minimal fields."""
        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        item = {
            "name": "Untitled",
            "permalink": "https://example.com",
        }

        result = client._parse_item(SearchResultType.NOTION, item)

        assert result is not None
        assert result.title == "Untitled"
        assert result.url == "https://example.com"

    def test_parse_item_with_nested_author(self) -> None:
        """Test parsing an item with nested author object."""
        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        item = {
            "title": "Issue",
            "url": "https://linear.app/issue",
            "assignee": {"name": "John Doe"},
        }

        result = client._parse_item(SearchResultType.LINEAR, item)

        assert result is not None
        assert result.author == "John Doe"
