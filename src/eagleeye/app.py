"""Main Slack bot application."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from slack_bolt import Ack, App, Respond, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

from eagleeye.config import Settings
from eagleeye.integrations.linear import LinearClient
from eagleeye.integrations.notion import NotionSearchClient
from eagleeye.integrations.slack_search import SlackSearchClient
from eagleeye.logging import get_logger
from eagleeye.models.search import SearchResult

logger = get_logger(__name__)


class EagleEyeBot:
    """Unified search Slack bot."""

    def __init__(self, settings: Settings) -> None:
        """Initialize bot with settings."""
        self.settings = settings

        # Initialize Slack app
        self.app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )

        # Initialize search clients
        self.slack_client = SlackSearchClient(settings.slack_bot_token)
        self.notion_client = NotionSearchClient(settings.notion_api_key)
        self.linear_client = LinearClient(settings.linear_api_key)

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register slash command and event handlers."""

        @self.app.command("/search")
        def handle_search_command(
            ack: Ack, command: dict[str, Any], respond: Respond
        ) -> None:
            """Handle /search slash command."""
            ack()

            query = command.get("text", "").strip()
            if not query:
                respond("Please provide a search query. Usage: `/search <query>`")
                return

            respond(f":mag: Searching for *{query}*...")

            results = self._unified_search(query)

            if not results:
                respond(f"No results found for *{query}*")
                return

            blocks = self._format_results_as_blocks(query, results)
            respond(blocks=blocks)

        @self.app.event("app_mention")
        def handle_mention(event: dict[str, Any], say: Say) -> None:
            """Handle @mentions of the bot."""
            text = event.get("text", "")
            # Remove bot mention from text
            query = " ".join(text.split()[1:]).strip()

            if not query:
                say("Hi! Use `/search <query>` to search.")
                return

            say(f":mag: Searching for *{query}*...")

            results = self._unified_search(query)

            if not results:
                say(f"No results found for *{query}*")
                return

            blocks = self._format_results_as_blocks(query, results)
            say(blocks=blocks)

    def _unified_search(self, query: str, limit: int = 3) -> list[SearchResult]:
        """Search across all integrations in parallel."""
        results: list[SearchResult] = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.slack_client.search, query, limit): "slack",
                executor.submit(self.notion_client.search, query, limit): "notion",
                executor.submit(self.linear_client.search, query, limit): "linear",
            }

            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as e:
                    source = futures[future]
                    logger.error(
                        "search_failed", source=source, error=str(e), query=query
                    )

        return results

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
        logger.info("bot_started", message="EagleEye bot is running")
        handler.start()  # type: ignore[no-untyped-call]
