"""Slack search integration."""

from typing import Any

from slack_sdk import WebClient

from eagleeye.logging import get_logger
from eagleeye.models.search import SearchResult, SearchResultType

logger = get_logger(__name__)


class SlackSearchClient:
    """Client for searching Slack messages and files."""

    def __init__(self, token: str) -> None:
        """Initialize with Slack bot token."""
        self.client = WebClient(token=token)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search Slack messages."""
        results: list[SearchResult] = []

        try:
            response = self.client.search_messages(query=query, count=limit)
            messages_data: dict[str, Any] = response.get("messages", {})
            messages: list[Any] = messages_data.get("matches", [])

            for msg in messages[:limit]:
                msg_dict: dict[str, Any] = msg
                permalink = msg_dict.get("permalink", "")
                text = msg_dict.get("text", "")[:200]
                username = msg_dict.get("username", "unknown")
                ts = msg_dict.get("ts", "")
                channel: dict[str, Any] = msg_dict.get("channel", {})
                channel_name = channel.get("name", "unknown")

                results.append(
                    SearchResult(
                        source=SearchResultType.SLACK,
                        title=f"#{channel_name}",
                        url=permalink,
                        snippet=text,
                        author=username,
                        timestamp=ts.split(".")[0] if ts else None,
                    )
                )
        except Exception as e:
            logger.error("slack_search_failed", error=str(e), query=query)

        return results
