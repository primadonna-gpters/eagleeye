"""Search result models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class SearchResultType(str, Enum):
    """Type of search result source."""

    SLACK = "slack"
    NOTION = "notion"
    LINEAR = "linear"


class SearchResult(BaseModel):
    """Unified search result from any integration."""

    source: SearchResultType
    title: str
    url: str
    snippet: str
    timestamp: str | None = None
    author: str | None = None
    extra: dict[str, str] | None = None

    def to_slack_block(self) -> dict[str, Any]:
        """Convert to Slack Block Kit format."""
        icon = {
            SearchResultType.SLACK: ":slack:",
            SearchResultType.NOTION: ":notion:",
            SearchResultType.LINEAR: ":linear:",
        }.get(self.source, ":mag:")

        text_parts = [f"{icon} *<{self.url}|{self.title}>*"]

        if self.snippet:
            text_parts.append(self.snippet[:200])

        if self.author:
            text_parts.append(f"_by {self.author}_")

        if self.timestamp:
            text_parts.append(
                f"<!date^{self.timestamp}^{{date_short}}|{self.timestamp}>"
            )

        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(text_parts),
            },
        }
