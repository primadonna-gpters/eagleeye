"""Tests for MCP client and server configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_integration.client import (
    SLACK_GET_CHANNEL_HISTORY,
    SLACK_LIST_CHANNELS,
    MCPConnection,
    MCPSearchClient,
    _server_type_to_result_type,
)
from mcp_integration.servers import (
    SEARCH_TOOL_NAMES,
    MCPServerConfig,
    ServerType,
    get_search_tool_arguments,
)
from models.search import SearchResultType


class TestMCPServerConfig:
    """Tests for MCP server configuration."""

    def test_slack_config(self) -> None:
        """Test Slack MCP server config creation."""
        config = MCPServerConfig.slack("xoxb-test-token")

        assert config.server_type == ServerType.SLACK
        assert config.command == "npx"
        assert "@modelcontextprotocol/server-slack" in config.args
        assert config.env["SLACK_BOT_TOKEN"] == "xoxb-test-token"

    def test_slack_config_with_team_id(self) -> None:
        """Test Slack MCP server config with team ID."""
        config = MCPServerConfig.slack("xoxb-test-token", team_id="T12345")

        assert config.env["SLACK_BOT_TOKEN"] == "xoxb-test-token"
        assert config.env["SLACK_TEAM_ID"] == "T12345"

    def test_notion_config(self) -> None:
        """Test Notion MCP server config creation."""
        config = MCPServerConfig.notion("secret_notion_key")

        assert config.server_type == ServerType.NOTION
        assert config.command == "npx"
        assert "@notionhq/notion-mcp-server" in config.args
        assert config.env["NOTION_TOKEN"] == "secret_notion_key"

    def test_linear_config(self) -> None:
        """Test Linear MCP server config creation."""
        config = MCPServerConfig.linear("lin_api_key")

        assert config.server_type == ServerType.LINEAR
        assert config.command == "npx"
        assert "@tacticlaunch/mcp-linear" in config.args
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
        """Test Slack search tool name (uses channel history as there's no search)."""
        assert SEARCH_TOOL_NAMES[ServerType.SLACK] == "slack_get_channel_history"

    def test_notion_tool_name(self) -> None:
        """Test Notion search tool name."""
        assert SEARCH_TOOL_NAMES[ServerType.NOTION] == "API-post-search"

    def test_linear_tool_name(self) -> None:
        """Test Linear search tool name."""
        assert SEARCH_TOOL_NAMES[ServerType.LINEAR] == "linear_searchIssues"

    def test_slack_tool_constants(self) -> None:
        """Test Slack tool name constants."""
        assert SLACK_LIST_CHANNELS == "slack_list_channels"
        assert SLACK_GET_CHANNEL_HISTORY == "slack_get_channel_history"


class TestGetSearchToolArguments:
    """Tests for search tool arguments."""

    def test_slack_arguments_without_channel(self) -> None:
        """Test Slack arguments without channel ID."""
        args = get_search_tool_arguments(ServerType.SLACK, "test query", limit=10)

        # Slack uses channel history, so query is not used
        assert args["limit"] == 10
        assert "channel_id" not in args

    def test_slack_arguments_with_channel(self) -> None:
        """Test Slack arguments with channel ID."""
        args = get_search_tool_arguments(
            ServerType.SLACK, "test query", limit=10, channel_id="C12345"
        )

        assert args["limit"] == 10
        assert args["channel_id"] == "C12345"

    def test_notion_arguments(self) -> None:
        """Test Notion search arguments."""
        args = get_search_tool_arguments(ServerType.NOTION, "test query", limit=5)

        assert args["query"] == "test query"
        assert args["page_size"] == 5

    def test_linear_arguments(self) -> None:
        """Test Linear search arguments."""
        args = get_search_tool_arguments(ServerType.LINEAR, "test query", limit=3)

        assert args["query"] == "test query"
        assert args["limit"] == 3


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

        with patch("mcp_integration.client.stdio_client") as mock_stdio:
            with patch("mcp_integration.client.ClientSession") as mock_session_class:
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


class TestSlackSearch:
    """Tests for Slack search functionality."""

    @pytest.mark.asyncio
    async def test_search_slack_filters_by_query(self) -> None:
        """Test that Slack search filters messages by query."""
        from mcp.types import TextContent

        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        mock_connection = MagicMock()
        mock_connection.session = MagicMock()

        # Mock channel list response
        channels_content = TextContent(
            type="text", text='[{"id": "C123", "name": "general"}]'
        )
        channels_result = MagicMock(content=[channels_content])

        # Mock channel history response with messages
        history_content = TextContent(
            type="text",
            text='[{"text": "Hello world", "user": "U123", "ts": "123.456"}, '
            '{"text": "Other message", "user": "U456", "ts": "789.012"}]',
        )
        history_result = MagicMock(content=[history_content])

        mock_connection.call_tool = AsyncMock(
            side_effect=[channels_result, history_result]
        )

        results = await client._search_slack(mock_connection, "hello", limit=5)

        # Should only return the message containing "hello"
        assert len(results) == 1
        assert results[0].snippet == "Hello world"
        assert results[0].title == "#general"

    @pytest.mark.asyncio
    async def test_search_slack_handles_empty_channels(self) -> None:
        """Test Slack search when no channels are returned."""
        from mcp.types import TextContent

        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        mock_connection = MagicMock()
        mock_connection.session = MagicMock()

        # Mock empty channel list
        channels_content = TextContent(type="text", text="[]")
        channels_result = MagicMock(content=[channels_content])

        mock_connection.call_tool = AsyncMock(return_value=channels_result)

        results = await client._search_slack(mock_connection, "test", limit=5)

        assert len(results) == 0

    def test_parse_slack_channels(self) -> None:
        """Test parsing Slack channels from MCP result."""
        from mcp.types import TextContent

        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        content = TextContent(
            type="text",
            text='[{"id": "C123", "name": "general"}, {"id": "C456", "name": "dev"}]',
        )
        result = MagicMock(content=[content])

        channels = client._parse_slack_channels(result)

        assert len(channels) == 2
        assert channels[0]["id"] == "C123"
        assert channels[1]["name"] == "dev"

    def test_parse_slack_history(self) -> None:
        """Test parsing Slack history and filtering by query."""
        from mcp.types import TextContent

        configs = [MCPServerConfig.slack("token")]
        client = MCPSearchClient(configs)

        content = TextContent(
            type="text",
            text='[{"text": "API error occurred", "user": "U123", "ts": "123.456"}, '
            '{"text": "Normal message", "user": "U456", "ts": "789.012"}]',
        )
        result = MagicMock(content=[content])
        channel = {"id": "C123", "name": "general"}

        results = client._parse_slack_history(result, channel, "api")

        assert len(results) == 1
        assert results[0].snippet == "API error occurred"
        assert results[0].source == SearchResultType.SLACK
