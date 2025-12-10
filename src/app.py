"""Main Slack bot application using Claude Agent SDK for unified search."""

import asyncio
import time
from typing import Any

from slack_bolt import Ack, App, Respond, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

from claude_agent import ClaudeSearchAgent
from config import Settings
from log_config import get_logger
from slack_formatter import (
    format_error_response,
    format_help_response,
    format_search_loading,
    format_search_response,
)

logger = get_logger(__name__)


class EagleEyeBot:
    """AI-powered unified search Slack bot using Claude Agent SDK."""

    def __init__(self, settings: Settings) -> None:
        """Initialize bot with settings."""
        self.settings = settings

        # Initialize Slack app
        self.app = App(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )

        # Initialize Claude search agent (SDK manages MCP servers directly)
        self.claude_agent = ClaudeSearchAgent(
            settings=settings,
            model=settings.claude_model,
        )

        # Event loop for async operations
        self._loop: asyncio.AbstractEventLoop | None = None

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register slash command and event handlers."""

        @self.app.command("/search")
        def handle_search_command(
            ack: Ack, command: dict[str, Any], respond: Respond
        ) -> None:
            """Handle /search slash command."""
            handler_start = time.perf_counter()
            logger.info("search_command_received", user=command.get("user_id"))
            ack()

            query = command.get("text", "").strip()
            if not query:
                respond(**format_help_response())
                return

            respond(**format_search_loading(query))
            loading_sent = time.perf_counter()
            logger.debug(
                "loading_message_sent",
                elapsed_ms=round((loading_sent - handler_start) * 1000, 2),
            )

            # Run Claude-powered search
            search_start = time.perf_counter()
            response = self._run_claude_search(query)
            search_elapsed = time.perf_counter() - search_start
            logger.info(
                "claude_search_returned",
                search_elapsed_ms=round(search_elapsed * 1000, 2),
                response_length=len(response),
            )

            if response.startswith("__ERROR__:"):
                error_msg = response[len("__ERROR__:"):]
                respond(**format_error_response(error_msg))
            else:
                respond(**format_search_response(response))

            total_elapsed = time.perf_counter() - handler_start
            logger.info(
                "search_command_completed",
                total_elapsed_ms=round(total_elapsed * 1000, 2),
                query=query,
            )

        @self.app.event("app_mention")
        def handle_mention(event: dict[str, Any], say: Say) -> None:
            """Handle @mentions of the bot."""
            handler_start = time.perf_counter()
            logger.info("mention_received", user=event.get("user"))

            text = event.get("text", "")
            # Remove bot mention from text
            query = " ".join(text.split()[1:]).strip()

            if not query:
                say(**format_help_response())
                return

            say(**format_search_loading(query))
            loading_sent = time.perf_counter()
            logger.debug(
                "loading_message_sent",
                elapsed_ms=round((loading_sent - handler_start) * 1000, 2),
            )

            # Run Claude-powered search
            search_start = time.perf_counter()
            response = self._run_claude_search(query)
            search_elapsed = time.perf_counter() - search_start
            logger.info(
                "claude_search_returned",
                search_elapsed_ms=round(search_elapsed * 1000, 2),
                response_length=len(response),
            )

            if response.startswith("__ERROR__:"):
                error_msg = response[len("__ERROR__:"):]
                say(**format_error_response(error_msg))
            else:
                say(**format_search_response(response))

            total_elapsed = time.perf_counter() - handler_start
            logger.info(
                "mention_completed",
                total_elapsed_ms=round(total_elapsed * 1000, 2),
                query=query,
            )

    def _run_claude_search(self, query: str) -> str:
        """Run Claude-powered search in a thread-safe way.

        Args:
            query: User's natural language query.

        Returns:
            Claude's formatted response.
        """
        if self._loop is None:
            self._loop = asyncio.new_event_loop()

        try:
            return self._loop.run_until_complete(self.claude_agent.search(query))
        except Exception as e:
            logger.error("claude_search_failed", error=str(e), query=query)
            # Return error as plain text - will be formatted by caller
            return f"__ERROR__:{e!s}"

    def start(self) -> None:
        """Start the bot using Socket Mode."""
        handler = SocketModeHandler(self.app, self.settings.slack_app_token)
        logger.info(
            "bot_started",
            message="EagleEye bot is running (Claude Agent SDK mode)",
        )
        handler.start()  # type: ignore[no-untyped-call]

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._loop:
            self._loop.close()
            self._loop = None
