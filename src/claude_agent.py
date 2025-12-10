"""Claude Agent SDK-based search agent using external MCP servers."""

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from config import Settings
from log_config import get_logger

logger = get_logger(__name__)


@dataclass
class SearchProgress:
    """Progress update during search."""

    status: str  # "thinking", "searching", "consolidating"
    current_tool: str | None = None
    completed_tools: list[str] | None = None


# Type alias for progress callback
ProgressCallback = Callable[[SearchProgress], Awaitable[None]]


# Keywords for detecting which MCP servers to use
SERVER_KEYWORDS: dict[str, list[str]] = {
    "slack": [
        "slack", "채널", "channel", "메시지", "message", "대화", "conversation",
    ],
    "notion": [
        "notion", "노션", "문서", "document", "페이지", "page", "wiki",
    ],
    "linear": [
        "linear", "리니어", "이슈", "issue", "티켓", "ticket",
        "버그", "bug", "태스크", "task",
    ],
    "github": [
        "github", "깃허브", "코드", "code", "pr", "pull request",
        "커밋", "commit", "레포", "repo",
    ],
}


def detect_relevant_servers(query: str) -> set[str]:
    """Detect which MCP servers are relevant for the query.

    Args:
        query: User's search query.

    Returns:
        Set of server names that should be used.
    """
    query_lower = query.lower()
    relevant: set[str] = set()

    for server, keywords in SERVER_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                relevant.add(server)
                break

    # If no specific servers detected, use all
    if not relevant:
        relevant = set(SERVER_KEYWORDS.keys())

    return relevant


def extract_server_from_tool_name(tool_name: str) -> str | None:
    """Extract server name from MCP tool name.

    Args:
        tool_name: Full tool name (e.g., "mcp__slack__slack_list_channels").

    Returns:
        Server name (e.g., "slack") or None.
    """
    match = re.match(r"mcp__(\w+)__", tool_name)
    return match.group(1) if match else None


# System prompt for the search agent
SYSTEM_PROMPT = """You are EagleEye, an intelligent search assistant.
You help users find information across Slack, Notion, Linear, and GitHub.

Your capabilities:
- Search Slack channels for messages and conversations
- Search Notion pages and documents
- Search Linear issues and projects
- Search GitHub repositories, code, issues, and pull requests

When a user asks a question:
1. Determine which platforms to search based on the query
2. Use the appropriate MCP tools to search
3. Analyze the results and provide a helpful, concise summary
4. Include relevant links so users can access the original content

Available MCP tools:
- Slack: mcp__slack__slack_list_channels, mcp__slack__slack_get_channel_history
- Notion: mcp__notion__API-post-search
- Linear: mcp__linear__linear_searchIssues
- GitHub: mcp__github__search_code, mcp__github__search_issues

For Slack search:
1. First use slack_list_channels to get available channels
2. Then use slack_get_channel_history on relevant channels
3. Filter results by keywords in your query

For GitHub search:
1. Use search_code to find code snippets matching keywords
2. Use search_issues to find issues and pull requests
3. Use get_file_contents to retrieve specific file contents
4. Use list_commits to see recent changes

Guidelines:
- Be concise but informative
- Highlight the most relevant findings
- If no results are found, suggest alternative search terms
- Always cite sources with links when available

## Slack Message Formatting (IMPORTANT)

You MUST format your responses using proper Slack mrkdwn syntax:

### Text Formatting
- *bold text* for emphasis and titles
- _italic text_ for secondary information
- ~strikethrough~ for deprecated/removed items
- `inline code` for technical terms, commands, file names
- ```code block``` for multi-line code or logs

### Links
- Use Slack link format: <URL|display text>
- Example: <https://notion.so/page123|Project Document>
- For Slack messages: <https://team.slack.com/archives/C123/p456|View message>

### Lists and Structure
- Use bullet points with • (not - or *)
- Keep each bullet concise (1-2 lines max)
- Group related items together

### Source Citations
- :slack: for Slack results
- :notion: for Notion results
- :linear: for Linear results
- :github: for GitHub results

### Response Structure Template
```
:mag: *검색 결과 요약*

[1-2 sentence summary of what was found]

:slack: *Slack*
• <link|#channel-name> - Brief description
  _by @username • date_
• <link|#channel-name> - Brief description

:notion: *Notion*
• <link|Page Title> - Brief description

:linear: *Linear*
• <link|ISSUE-123> - Issue title (_status_)

:github: *GitHub*
• <link|repo/path/file.py> - Code snippet description
• <link|repo#123> - Issue/PR title (_status_)

---
_총 N개의 관련 결과를 찾았습니다._
```

### Important Rules
1. ALWAYS use <URL|text> format for links, never plain URLs
2. Use emoji prefixes (:slack:, :notion:, :linear:, :github:) before each source section
3. Include author/assignee with _italic_ when available
4. Keep snippets under 100 characters, use ellipsis (...) if truncated
5. End with a summary count of total results found
6. Use --- horizontal rule to separate summary from main content
"""


def create_mcp_server_configs(settings: Settings) -> dict[str, Any]:
    """Create MCP server configurations for Claude Agent SDK.

    Args:
        settings: Application settings with API keys.

    Returns:
        Dictionary of MCP server configurations.
    """
    configs: dict[str, Any] = {}

    if settings.enable_slack_mcp:
        configs["slack"] = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": settings.slack_bot_token,
                "SLACK_TEAM_ID": settings.slack_team_id,
            },
        }

    if settings.enable_notion_mcp:
        notion_headers = (
            f'{{"Authorization": "Bearer {settings.notion_api_key}", '
            f'"Notion-Version": "2022-06-28"}}'
        )
        configs["notion"] = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {
                "OPENAPI_MCP_HEADERS": notion_headers,
            },
        }

    if settings.enable_linear_mcp:
        configs["linear"] = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@tacticlaunch/mcp-linear"],
            "env": {
                "LINEAR_API_KEY": settings.linear_api_key,
            },
        }

    if settings.enable_github_mcp and settings.github_token:
        configs["github"] = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token,
            },
        }

    return configs


class ClaudeSearchAgent:
    """AI-powered search agent using Claude Agent SDK with external MCP servers."""

    def __init__(
        self,
        settings: Settings,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """Initialize the Claude search agent.

        Args:
            settings: Application settings with API keys.
            model: Claude model to use.
        """
        self.settings = settings
        self.model = model

        # Create MCP server configurations
        self.mcp_servers = create_mcp_server_configs(settings)

        # Build allowed tools list based on enabled servers
        self.allowed_tools = self._build_allowed_tools()

        logger.info(
            "claude_agent_initialized",
            mcp_servers=list(self.mcp_servers.keys()),
            model=model,
        )

    def _build_allowed_tools(self) -> list[str]:
        """Build list of allowed MCP tools based on enabled servers."""
        tools: list[str] = []

        if self.settings.enable_slack_mcp:
            tools.extend([
                "mcp__slack__slack_list_channels",
                "mcp__slack__slack_get_channel_history",
                "mcp__slack__slack_get_thread_replies",
            ])

        if self.settings.enable_notion_mcp:
            tools.extend([
                "mcp__notion__API-post-search",
                "mcp__notion__API-retrieve-a-page",
                "mcp__notion__API-get-block-children",
            ])

        if self.settings.enable_linear_mcp:
            tools.extend([
                "mcp__linear__linear_searchIssues",
                "mcp__linear__linear_getIssueById",
                "mcp__linear__linear_getIssues",
            ])

        if self.settings.enable_github_mcp and self.settings.github_token:
            tools.extend([
                "mcp__github__search_repositories",
                "mcp__github__search_code",
                "mcp__github__search_issues",
                "mcp__github__get_file_contents",
                "mcp__github__list_commits",
                "mcp__github__get_issue",
                "mcp__github__get_pull_request",
                "mcp__github__list_issues",
                "mcp__github__list_pull_requests",
            ])

        return tools

    def _filter_servers_for_query(
        self, user_query: str
    ) -> tuple[dict[str, Any], list[str]]:
        """Filter MCP servers and tools based on the query.

        Args:
            user_query: User's search query.

        Returns:
            Tuple of (filtered_servers, filtered_tools).
        """
        relevant = detect_relevant_servers(user_query)

        # Filter servers
        filtered_servers = {
            name: config
            for name, config in self.mcp_servers.items()
            if name in relevant
        }

        # Filter tools
        filtered_tools = [
            tool
            for tool in self.allowed_tools
            if extract_server_from_tool_name(tool) in relevant
        ]

        logger.debug(
            "servers_filtered",
            query=user_query,
            relevant_servers=list(relevant),
            filtered_servers=list(filtered_servers.keys()),
            filtered_tools_count=len(filtered_tools),
        )

        return filtered_servers, filtered_tools

    async def search(
        self,
        user_query: str,
        on_progress: ProgressCallback | None = None,
    ) -> str:
        """Process a search query using Claude Agent SDK.

        Args:
            user_query: User's natural language query.
            on_progress: Optional callback for progress updates.

        Returns:
            Claude's formatted response with search results.
        """
        total_start = time.perf_counter()
        logger.info("claude_search_started", query=user_query)

        # Filter servers based on query (speed optimization)
        filtered_servers, filtered_tools = self._filter_servers_for_query(user_query)

        # Notify: thinking
        if on_progress:
            await on_progress(SearchProgress(status="thinking"))

        # Configure query options
        options_start = time.perf_counter()
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers=filtered_servers,
            allowed_tools=filtered_tools,
            model=self.model,
            permission_mode="bypassPermissions",
            max_turns=15,  # Allow enough turns for multi-step search
        )
        logger.debug(
            "options_created",
            elapsed_ms=round((time.perf_counter() - options_start) * 1000, 2),
        )

        try:
            final_response = ""
            turn_count = 0
            tool_calls: list[dict[str, Any]] = []
            completed_servers: list[str] = []
            current_server: str | None = None
            first_message_time: float | None = None
            last_message_time = time.perf_counter()

            query_start = time.perf_counter()
            logger.debug("query_stream_starting")

            async for message in query(prompt=user_query, options=options):
                current_time = time.perf_counter()

                if first_message_time is None:
                    first_message_time = current_time - query_start
                    logger.info(
                        "first_message_received",
                        elapsed_ms=round(first_message_time * 1000, 2),
                        message_type=type(message).__name__,
                    )

                turn_count += 1
                message_elapsed = current_time - last_message_time
                last_message_time = current_time

                # Log tool use and result blocks
                if isinstance(message, AssistantMessage):
                    for block in getattr(message, "content", []):
                        if isinstance(block, ToolUseBlock):
                            tool_start = time.perf_counter()
                            tool_info = {
                                "tool_name": block.name,
                                "turn": turn_count,
                                "start_time": tool_start - total_start,
                            }
                            tool_calls.append(tool_info)

                            # Extract server name and notify progress
                            server = extract_server_from_tool_name(block.name)
                            if server and server != current_server:
                                if (
                                    current_server
                                    and current_server not in completed_servers
                                ):
                                    completed_servers.append(current_server)
                                current_server = server

                                if on_progress:
                                    await on_progress(
                                        SearchProgress(
                                            status="searching",
                                            current_tool=server,
                                            completed_tools=completed_servers.copy(),
                                        )
                                    )

                            logger.debug(
                                "tool_use_requested",
                                tool_name=block.name,
                                turn=turn_count,
                                elapsed_since_start_ms=round(
                                    (tool_start - total_start) * 1000, 2
                                ),
                            )
                        elif isinstance(block, ToolResultBlock):
                            logger.debug(
                                "tool_result_received",
                                turn=turn_count,
                                elapsed_ms=round(message_elapsed * 1000, 2),
                                elapsed_since_start_ms=round(
                                    (current_time - total_start) * 1000, 2
                                ),
                            )

                # Extract text from assistant messages
                if isinstance(message, (AssistantMessage, ResultMessage)):
                    logger.debug(
                        "message_received",
                        message_type=type(message).__name__,
                        turn=turn_count,
                        elapsed_ms=round(message_elapsed * 1000, 2),
                    )
                    for block in getattr(message, "content", []):
                        if isinstance(block, TextBlock):
                            final_response = block.text
                            # Notify: consolidating (when we get final text)
                            if on_progress and current_server:
                                if current_server not in completed_servers:
                                    completed_servers.append(current_server)
                                await on_progress(
                                    SearchProgress(
                                        status="consolidating",
                                        completed_tools=completed_servers.copy(),
                                    )
                                )

            total_elapsed = time.perf_counter() - total_start
            logger.info(
                "claude_search_completed",
                query=user_query,
                total_elapsed_ms=round(total_elapsed * 1000, 2),
                total_turns=turn_count,
                tool_calls_count=len(tool_calls),
                tool_names=[t["tool_name"] for t in tool_calls],
            )
            return final_response or "검색 결과를 찾지 못했습니다."

        except Exception as e:
            total_elapsed = time.perf_counter() - total_start
            logger.error(
                "claude_search_failed",
                error=str(e),
                query=user_query,
                elapsed_ms=round(total_elapsed * 1000, 2),
            )
            raise
