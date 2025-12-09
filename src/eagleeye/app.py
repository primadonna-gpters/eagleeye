"""Main Slack bot application using MCP for unified search."""

import asyncio
import re
from dataclasses import dataclass
from typing import Any

from slack_bolt import Ack, App, Respond, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

from eagleeye.config import Settings
from eagleeye.logging import get_logger
from eagleeye.mcp.client import MCPSearchClient
from eagleeye.mcp.servers import MCPServerConfig
from eagleeye.models.search import SearchResult

logger = get_logger(__name__)

# Filter flags pattern: --slack, --notion, --linear
FILTER_FLAGS_PATTERN = re.compile(r"--(?:slack|notion|linear)\b", re.IGNORECASE)


@dataclass
class ParsedQuery:
    """Parsed search query with filters."""

    query: str
    sources: set[str]  # Empty means all sources


class EagleEyeBot:
    """Unified search Slack bot using MCP."""

    def __init__(self, settings: Settings) -> None:
        """Initialize bot with settings."""
        self.settings = settings

        # Initialize Slack app
        self.app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )

        # Initialize MCP search client
        self.mcp_client = self._create_mcp_client()

        # Event loop for async operations
        self._loop: asyncio.AbstractEventLoop | None = None

        # Register handlers
        self._register_handlers()

    def _create_mcp_client(self) -> MCPSearchClient:
        """Create MCP search client with configured servers."""
        configs: list[MCPServerConfig] = []

        if self.settings.enable_slack_mcp:
            configs.append(MCPServerConfig.slack(self.settings.slack_bot_token))

        if self.settings.enable_notion_mcp:
            configs.append(MCPServerConfig.notion(self.settings.notion_api_key))

        if self.settings.enable_linear_mcp:
            configs.append(MCPServerConfig.linear(self.settings.linear_api_key))

        return MCPSearchClient(configs)

    @staticmethod
    def parse_query(text: str) -> ParsedQuery:
        """Parse query text and extract filter flags.

        Args:
            text: Raw query text, e.g., "--slack --notion api error"

        Returns:
            ParsedQuery with cleaned query and source filters
        """
        sources: set[str] = set()
        flags = FILTER_FLAGS_PATTERN.findall(text)

        for flag in flags:
            source = flag.lstrip("-").lower()
            sources.add(source)

        # Remove flags from query
        query = FILTER_FLAGS_PATTERN.sub("", text).strip()
        # Clean up multiple spaces
        query = " ".join(query.split())

        return ParsedQuery(query=query, sources=sources)

    def _register_handlers(self) -> None:
        """Register slash command and event handlers."""

        @self.app.command("/search")
        def handle_search_command(
            ack: Ack, command: dict[str, Any], respond: Respond
        ) -> None:
            """Handle /search slash command."""
            ack()

            raw_text = command.get("text", "").strip()
            if not raw_text:
                respond(
                    "Please provide a search query.\n"
                    "Usage: `/search <query>` or `/search --slack --notion <query>`\n"
                    "Filters: `--slack`, `--notion`, `--linear`"
                )
                return

            parsed = self.parse_query(raw_text)

            if not parsed.query:
                respond("Please provide a search query after the filter flags.")
                return

            source_hint = (
                f" in *{', '.join(sorted(parsed.sources))}*" if parsed.sources else ""
            )
            respond(f":mag: Searching for *{parsed.query}*{source_hint}...")

            results = self._run_async_search(parsed.query, sources=parsed.sources)

            if not results:
                respond(f"No results found for *{parsed.query}*")
                return

            blocks = self._format_results_as_blocks(parsed.query, results)
            respond(blocks=blocks)

        @self.app.event("app_mention")
        def handle_mention(event: dict[str, Any], say: Say) -> None:
            """Handle @mentions of the bot."""
            text = event.get("text", "")
            # Remove bot mention from text
            raw_text = " ".join(text.split()[1:]).strip()

            if not raw_text:
                say(
                    "Hi! Use `/search <query>` to search.\n"
                    "Filters: `--slack`, `--notion`, `--linear`"
                )
                return

            parsed = self.parse_query(raw_text)

            if not parsed.query:
                say("Please provide a search query after the filter flags.")
                return

            source_hint = (
                f" in *{', '.join(sorted(parsed.sources))}*" if parsed.sources else ""
            )
            say(f":mag: Searching for *{parsed.query}*{source_hint}...")

            results = self._run_async_search(parsed.query, sources=parsed.sources)

            if not results:
                say(f"No results found for *{parsed.query}*")
                return

            blocks = self._format_results_as_blocks(parsed.query, results)
            say(blocks=blocks)

    def _run_async_search(
        self,
        query: str,
        sources: set[str] | None = None,
        limit: int = 3,
    ) -> list[SearchResult]:
        """Run async MCP search in a thread-safe way."""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()

        try:
            return self._loop.run_until_complete(
                self.mcp_client.search(query, sources=sources, limit=limit)
            )
        except Exception as e:
            logger.error("search_failed", error=str(e), query=query)
            return []

    def _format_results_as_blocks(
        self, query: str, results: list[SearchResult]
    ) -> list[dict[str, Any]]:
        """Format search results as Slack blocks."""
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Search results for: {query}",
                },
            },
            {"type": "divider"},
        ]

        # Group by source
        by_source: dict[str, list[SearchResult]] = {}
        for result in results:
            source_name = result.source.value
            if source_name not in by_source:
                by_source[source_name] = []
            by_source[source_name].append(result)

        # Add results by source
        for source_name, source_results in by_source.items():
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{source_name.title()}* ({len(source_results)})",
                    },
                }
            )

            for result in source_results:
                blocks.append(result.to_slack_block())

            blocks.append({"type": "divider"})

        return blocks

    def start(self) -> None:
        """Start the bot using Socket Mode."""
        handler = SocketModeHandler(self.app, self.settings.slack_app_token)
        logger.info("bot_started", message="EagleEye bot is running (MCP mode)")
        handler.start()  # type: ignore[no-untyped-call]

    async def cleanup(self) -> None:
        """Cleanup MCP connections."""
        await self.mcp_client.disconnect_all()
        if self._loop:
            self._loop.close()
            self._loop = None
