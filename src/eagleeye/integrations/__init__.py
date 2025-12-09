"""Integration modules for external services."""

from eagleeye.integrations.linear import LinearClient
from eagleeye.integrations.notion import NotionSearchClient
from eagleeye.integrations.slack_search import SlackSearchClient

__all__ = ["LinearClient", "NotionSearchClient", "SlackSearchClient"]
