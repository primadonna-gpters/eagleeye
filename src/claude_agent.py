"""Claude Agent SDK-based search agent using external MCP servers."""

import time
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

# System prompt for the search agent
SYSTEM_PROMPT = """You are EagleEye, an intelligent search assistant.
You help users find information across Slack, Notion, and Linear.

Your capabilities:
- Search Slack channels for messages and conversations
- Search Notion pages and documents
- Search Linear issues and projects

When a user asks a question:
1. Determine which platforms to search based on the query
2. Use the appropriate MCP tools to search
3. Analyze the results and provide a helpful, concise summary
4. Include relevant links so users can access the original content

Available MCP tools:
- Slack: mcp__slack__slack_list_channels, mcp__slack__slack_get_channel_history
- Notion: mcp__notion__API-post-search
- Linear: mcp__linear__linear_searchIssues

For Slack search:
1. First use slack_list_channels to get available channels
2. Then use slack_get_channel_history on relevant channels
3. Filter results by keywords in your query

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

---
_총 N개의 관련 결과를 찾았습니다._
```

### Important Rules
1. ALWAYS use <URL|text> format for links, never plain URLs
2. Use emoji prefixes (:slack:, :notion:, :linear:) before each source section
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

        return tools

    async def search(self, user_query: str) -> str:
        """Process a search query using Claude Agent SDK.

        Args:
            user_query: User's natural language query.

        Returns:
            Claude's formatted response with search results.
        """
        total_start = time.perf_counter()
        logger.info("claude_search_started", query=user_query)

        # Configure query options
        options_start = time.perf_counter()
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers=self.mcp_servers,
            allowed_tools=self.allowed_tools,
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
