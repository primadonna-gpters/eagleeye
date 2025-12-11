"""Tests for Claude Agent SDK search agent."""

from unittest.mock import MagicMock, patch

import pytest

from claude_agent import (
    ClaudeSearchAgent,
    SearchProgress,
    create_mcp_server_configs,
    detect_relevant_servers,
    extract_server_from_tool_name,
)
from config import Settings


class TestDetectRelevantServers:
    """Tests for server detection based on query keywords."""

    def test_detect_slack_keywords(self) -> None:
        """Test detecting Slack-related queries."""
        assert "slack" in detect_relevant_servers("slack 채널에서 찾아줘")
        assert "slack" in detect_relevant_servers("Check the channel history")
        assert "slack" in detect_relevant_servers("메시지 검색")

    def test_detect_notion_keywords(self) -> None:
        """Test detecting Notion-related queries."""
        assert "notion" in detect_relevant_servers("노션 문서 찾아줘")
        assert "notion" in detect_relevant_servers("Search Notion pages")
        assert "notion" in detect_relevant_servers("wiki page about API")

    def test_detect_linear_keywords(self) -> None:
        """Test detecting Linear-related queries."""
        assert "linear" in detect_relevant_servers("리니어 이슈 검색")
        assert "linear" in detect_relevant_servers("Find bug tickets")
        assert "linear" in detect_relevant_servers("태스크 목록")

    def test_detect_github_keywords(self) -> None:
        """Test detecting GitHub-related queries."""
        assert "github" in detect_relevant_servers("깃허브 코드 검색")
        assert "github" in detect_relevant_servers("Find PR for authentication")
        assert "github" in detect_relevant_servers("레포 커밋 히스토리")

    def test_detect_multiple_servers(self) -> None:
        """Test detecting multiple servers in one query."""
        servers = detect_relevant_servers("slack 채널과 notion 문서에서 찾아줘")
        assert "slack" in servers
        assert "notion" in servers

    def test_fallback_to_all_servers(self) -> None:
        """Test fallback to all servers when no keywords match."""
        servers = detect_relevant_servers("오늘 회의 내용 정리해줘")
        assert len(servers) == 4
        assert "slack" in servers
        assert "notion" in servers
        assert "linear" in servers
        assert "github" in servers

    def test_case_insensitive(self) -> None:
        """Test that detection is case-insensitive."""
        assert "slack" in detect_relevant_servers("SLACK")
        assert "github" in detect_relevant_servers("GitHub")


class TestExtractServerFromToolName:
    """Tests for extracting server name from tool name."""

    def test_extract_slack_server(self) -> None:
        """Test extracting slack from tool name."""
        tool_name = "mcp__slack__slack_list_channels"
        assert extract_server_from_tool_name(tool_name) == "slack"

    def test_extract_notion_server(self) -> None:
        """Test extracting notion from tool name."""
        tool_name = "mcp__notion__API-post-search"
        assert extract_server_from_tool_name(tool_name) == "notion"

    def test_extract_linear_server(self) -> None:
        """Test extracting linear from tool name."""
        tool_name = "mcp__linear__linear_searchIssues"
        assert extract_server_from_tool_name(tool_name) == "linear"

    def test_extract_github_server(self) -> None:
        """Test extracting github from tool name."""
        tool_name = "mcp__github__search_code"
        assert extract_server_from_tool_name(tool_name) == "github"

    def test_invalid_tool_name(self) -> None:
        """Test with invalid tool name format."""
        assert extract_server_from_tool_name("invalid_tool") is None
        assert extract_server_from_tool_name("") is None


class TestSearchProgress:
    """Tests for SearchProgress dataclass."""

    def test_search_progress_thinking(self) -> None:
        """Test thinking status."""
        progress = SearchProgress(status="thinking")
        assert progress.status == "thinking"
        assert progress.current_tool is None
        assert progress.completed_tools is None

    def test_search_progress_searching(self) -> None:
        """Test searching status with tools."""
        progress = SearchProgress(
            status="searching",
            current_tool="slack",
            completed_tools=["notion"],
        )
        assert progress.status == "searching"
        assert progress.current_tool == "slack"
        assert progress.completed_tools == ["notion"]

    def test_search_progress_consolidating(self) -> None:
        """Test consolidating status."""
        progress = SearchProgress(
            status="consolidating",
            completed_tools=["slack", "notion", "linear"],
        )
        assert progress.status == "consolidating"
        assert len(progress.completed_tools) == 3


class TestCreateMCPServerConfigs:
    """Tests for MCP server configuration creation."""

    def test_all_servers_enabled(self) -> None:
        """Test config with all servers enabled."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = True
        settings.enable_notion_mcp = True
        settings.enable_linear_mcp = True
        settings.enable_github_mcp = True
        settings.slack_bot_token = "xoxb-test"
        settings.slack_team_id = "T12345"
        settings.notion_api_key = "secret_notion"
        settings.linear_api_key = "lin_api"
        settings.github_token = "ghp_test"

        configs = create_mcp_server_configs(settings)

        assert "slack" in configs
        assert "notion" in configs
        assert "linear" in configs
        assert "github" in configs

    def test_slack_config_structure(self) -> None:
        """Test Slack server config structure."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = True
        settings.enable_notion_mcp = False
        settings.enable_linear_mcp = False
        settings.enable_github_mcp = False
        settings.slack_bot_token = "xoxb-test"
        settings.slack_team_id = "T12345"

        configs = create_mcp_server_configs(settings)

        assert configs["slack"]["type"] == "stdio"
        assert configs["slack"]["command"] == "npx"
        assert "@modelcontextprotocol/server-slack" in configs["slack"]["args"]
        assert configs["slack"]["env"]["SLACK_BOT_TOKEN"] == "xoxb-test"
        assert configs["slack"]["env"]["SLACK_TEAM_ID"] == "T12345"

    def test_notion_config_structure(self) -> None:
        """Test Notion server config structure."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = False
        settings.enable_notion_mcp = True
        settings.enable_linear_mcp = False
        settings.enable_github_mcp = False
        settings.notion_api_key = "secret_notion"

        configs = create_mcp_server_configs(settings)

        assert configs["notion"]["type"] == "stdio"
        assert configs["notion"]["command"] == "npx"
        assert "@notionhq/notion-mcp-server" in configs["notion"]["args"]
        assert "OPENAPI_MCP_HEADERS" in configs["notion"]["env"]

    def test_linear_config_structure(self) -> None:
        """Test Linear server config structure."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = False
        settings.enable_notion_mcp = False
        settings.enable_linear_mcp = True
        settings.enable_github_mcp = False
        settings.linear_api_key = "lin_api"

        configs = create_mcp_server_configs(settings)

        assert configs["linear"]["type"] == "stdio"
        assert configs["linear"]["command"] == "npx"
        assert "@tacticlaunch/mcp-linear" in configs["linear"]["args"]
        assert configs["linear"]["env"]["LINEAR_API_KEY"] == "lin_api"

    def test_github_config_structure(self) -> None:
        """Test GitHub server config structure."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = False
        settings.enable_notion_mcp = False
        settings.enable_linear_mcp = False
        settings.enable_github_mcp = True
        settings.github_token = "ghp_test"

        configs = create_mcp_server_configs(settings)

        assert configs["github"]["type"] == "stdio"
        assert configs["github"]["command"] == "npx"
        assert "@modelcontextprotocol/server-github" in configs["github"]["args"]
        assert configs["github"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_test"

    def test_github_disabled_without_token(self) -> None:
        """Test GitHub is disabled when no token provided."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = False
        settings.enable_notion_mcp = False
        settings.enable_linear_mcp = False
        settings.enable_github_mcp = True
        settings.github_token = ""  # Empty token

        configs = create_mcp_server_configs(settings)

        assert "github" not in configs

    def test_no_servers_enabled(self) -> None:
        """Test empty config when no servers enabled."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = False
        settings.enable_notion_mcp = False
        settings.enable_linear_mcp = False
        settings.enable_github_mcp = False

        configs = create_mcp_server_configs(settings)

        assert len(configs) == 0


class TestClaudeSearchAgent:
    """Tests for ClaudeSearchAgent class."""

    def _create_mock_settings(
        self,
        enable_slack: bool = True,
        enable_notion: bool = True,
        enable_linear: bool = True,
        enable_github: bool = True,
        github_org: str = "",
    ) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock(spec=Settings)
        settings.enable_slack_mcp = enable_slack
        settings.enable_notion_mcp = enable_notion
        settings.enable_linear_mcp = enable_linear
        settings.enable_github_mcp = enable_github
        settings.slack_bot_token = "xoxb-test"
        settings.slack_team_id = "T12345"
        settings.notion_api_key = "secret_notion"
        settings.linear_api_key = "lin_api"
        settings.github_token = "ghp_test" if enable_github else ""
        settings.github_org = github_org
        settings.debug = False
        return settings

    def test_agent_initialization(self) -> None:
        """Test agent initialization with all servers."""
        settings = self._create_mock_settings()

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        assert "slack" in agent.mcp_servers
        assert "notion" in agent.mcp_servers
        assert "linear" in agent.mcp_servers
        assert "github" in agent.mcp_servers
        assert len(agent.allowed_tools) > 0

    def test_agent_builds_allowed_tools(self) -> None:
        """Test that allowed tools list is built correctly."""
        settings = self._create_mock_settings(
            enable_slack=True,
            enable_notion=False,
            enable_linear=False,
            enable_github=False,
        )

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        # Should only have Slack tools
        assert any("slack" in tool for tool in agent.allowed_tools)
        assert not any("notion" in tool for tool in agent.allowed_tools)
        assert not any("linear" in tool for tool in agent.allowed_tools)
        assert not any("github" in tool for tool in agent.allowed_tools)

    def test_agent_system_prompt_without_github_org(self) -> None:
        """Test system prompt without GitHub org filter."""
        settings = self._create_mock_settings(github_org="")

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        assert "ONLY search within" not in agent.system_prompt

    def test_agent_system_prompt_with_github_org(self) -> None:
        """Test system prompt includes GitHub org filter."""
        settings = self._create_mock_settings(github_org="my-company")

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        assert 'ONLY search within the "my-company" organization' in agent.system_prompt
        assert "org:my-company" in agent.system_prompt

    def test_filter_servers_for_query(self) -> None:
        """Test query-based server filtering."""
        settings = self._create_mock_settings()

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        # Query mentioning slack should filter to slack only
        filtered_servers, filtered_tools = agent._filter_servers_for_query(
            "slack 채널에서 찾아줘"
        )

        assert "slack" in filtered_servers
        assert "notion" not in filtered_servers
        assert any("slack" in tool for tool in filtered_tools)

    def test_filter_servers_fallback(self) -> None:
        """Test server filtering falls back to all when no keywords match."""
        settings = self._create_mock_settings()

        with patch("claude_agent.logger"):
            agent = ClaudeSearchAgent(settings)

        # Generic query should return all servers
        filtered_servers, filtered_tools = agent._filter_servers_for_query(
            "오늘 회의 내용"
        )

        assert "slack" in filtered_servers
        assert "notion" in filtered_servers
        assert "linear" in filtered_servers
        assert "github" in filtered_servers
