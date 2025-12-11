"""Main Slack bot application using Claude Agent SDK for unified search."""

import asyncio
import time
from typing import Any

from slack_bolt import App, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from claude_agent import ClaudeSearchAgent, SearchProgress
from config import Settings
from log_config import get_logger
from slack_formatter import (
    format_error_response,
    format_help_response,
    format_search_loading,
    format_search_progress,
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

        # WebClient for chat.update
        self.client: WebClient = self.app.client

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register event handlers."""

        @self.app.event("app_mention")
        def handle_mention(event: dict[str, Any], say: Say) -> None:
            """Handle @mentions of the bot."""
            handler_start = time.perf_counter()
            logger.info("mention_received", user=event.get("user"))

            text = event.get("text", "")
            channel_id = event.get("channel", "")
            # Remove bot mention from text
            query = " ".join(text.split()[1:]).strip()

            if not query:
                say(**format_help_response())
                return

            # Post initial loading message and get ts for updates
            loading_payload = format_search_loading(query)
            try:
                result = self.client.chat_postMessage(
                    channel=channel_id,
                    text=loading_payload.get("text", ""),
                    blocks=loading_payload.get("blocks", []),
                )
                message_ts = result.get("ts", "")
            except SlackApiError as e:
                logger.error("loading_message_failed", error=str(e))
                say(**format_search_loading(query))
                message_ts = ""

            loading_sent = time.perf_counter()
            logger.debug(
                "loading_message_sent",
                elapsed_ms=round((loading_sent - handler_start) * 1000, 2),
            )

            # Run Claude-powered search with progress updates
            search_start = time.perf_counter()
            if message_ts and channel_id:
                response = self._run_claude_search_with_progress(
                    query, channel_id, message_ts
                )
            else:
                response = self._run_claude_search(query)

            search_elapsed = time.perf_counter() - search_start
            logger.info(
                "claude_search_returned",
                search_elapsed_ms=round(search_elapsed * 1000, 2),
                response_length=len(response),
            )

            # Update the message with final response
            if response.startswith("__ERROR__:"):
                error_msg = response[len("__ERROR__:"):]
                final_payload = format_error_response(error_msg)
            else:
                final_payload = format_search_response(response)

            if message_ts and channel_id:
                self._update_message(channel_id, message_ts, final_payload)
            else:
                say(**final_payload)

            total_elapsed = time.perf_counter() - handler_start
            logger.info(
                "mention_completed",
                total_elapsed_ms=round(total_elapsed * 1000, 2),
                query=query,
            )

    def _update_message(
        self,
        channel: str,
        ts: str,
        payload: dict[str, Any],
    ) -> None:
        """Update a Slack message using chat.update.

        Args:
            channel: Channel ID.
            ts: Message timestamp.
            payload: Message payload with blocks and text.
        """
        try:
            self.client.chat_update(
                channel=channel,
                ts=ts,
                text=payload.get("text", ""),
                blocks=payload.get("blocks", []),
            )
        except SlackApiError as e:
            logger.warning(
                "message_update_failed",
                error=str(e),
                channel=channel,
                ts=ts,
            )

    def _run_claude_search(self, query: str) -> str:
        """Run Claude-powered search in a thread-safe way (legacy, no progress).

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
            return f"__ERROR__:{e!s}"

    def _run_claude_search_with_progress(
        self,
        query: str,
        channel: str,
        message_ts: str,
    ) -> str:
        """Run Claude-powered search with real-time progress updates.

        Args:
            query: User's natural language query.
            channel: Channel ID for progress updates.
            message_ts: Message timestamp to update.

        Returns:
            Claude's formatted response.
        """
        if self._loop is None:
            self._loop = asyncio.new_event_loop()

        async def on_progress(progress: SearchProgress) -> None:
            """Handle progress updates from Claude agent."""
            payload = format_search_progress(
                query=query,
                current_tool=progress.current_tool,
                completed_tools=progress.completed_tools,
                status=progress.status,
            )
            self._update_message(channel, message_ts, payload)
            logger.debug(
                "progress_updated",
                status=progress.status,
                current_tool=progress.current_tool,
                completed_tools=progress.completed_tools,
            )

        try:
            return self._loop.run_until_complete(
                self.claude_agent.search(query, on_progress=on_progress)
            )
        except Exception as e:
            logger.error("claude_search_failed", error=str(e), query=query)
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
