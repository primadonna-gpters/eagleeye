"""Notion search integration."""

from typing import Any

from notion_client import Client

from eagleeye.logging import get_logger
from eagleeye.models.search import SearchResult, SearchResultType

logger = get_logger(__name__)


class NotionSearchClient:
    """Client for searching Notion pages and databases."""

    def __init__(self, api_key: str) -> None:
        """Initialize with Notion API key."""
        self.client = Client(auth=api_key)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search Notion pages."""
        results: list[SearchResult] = []

        try:
            response: dict[str, Any] = self.client.search(  # type: ignore[assignment]
                query=query, page_size=limit
            )

            for item in response.get("results", [])[:limit]:
                object_type = item.get("object")
                item_id = item.get("id", "")

                # Extract title based on object type
                title = self._extract_title(item)
                url = item.get("url", f"https://notion.so/{item_id.replace('-', '')}")

                # Extract snippet from properties or content
                snippet = self._extract_snippet(item)

                results.append(
                    SearchResult(
                        source=SearchResultType.NOTION,
                        title=title or "Untitled",
                        url=url,
                        snippet=snippet,
                        extra={"type": object_type} if object_type else None,
                    )
                )
        except Exception as e:
            logger.error("notion_search_failed", error=str(e), query=query)

        return results

    def _extract_title(self, item: dict[str, Any]) -> str:
        """Extract title from Notion item."""
        properties = item.get("properties", {})

        # Try common title property names
        for prop_name in ["title", "Title", "Name", "name"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "title":
                    title_list = prop.get("title", [])
                    if title_list:
                        result: str = title_list[0].get("plain_text", "")
                        return result

        # Fallback for page titles
        if "title" in item:
            title_list = item["title"]
            if isinstance(title_list, list) and title_list:
                text: str = title_list[0].get("plain_text", "")
                return text

        return ""

    def _extract_snippet(self, item: dict[str, Any]) -> str:
        """Extract snippet from Notion item."""
        properties = item.get("properties", {})

        # Try to get description or content property
        for prop_name in ["Description", "description", "Content", "content"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "rich_text":
                    text_list = prop.get("rich_text", [])
                    if text_list:
                        snippet: str = text_list[0].get("plain_text", "")[:200]
                        return snippet

        return ""
