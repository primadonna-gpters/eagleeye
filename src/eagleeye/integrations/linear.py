"""Linear search integration."""

import httpx

from eagleeye.logging import get_logger
from eagleeye.models.search import SearchResult, SearchResultType

logger = get_logger(__name__)

GRAPHQL_URL = "https://api.linear.app/graphql"

SEARCH_QUERY = """
query SearchIssues($query: String!, $first: Int) {
  searchIssues(query: $query, first: $first) {
    nodes {
      id
      identifier
      title
      description
      url
      state {
        name
      }
      assignee {
        name
      }
      createdAt
    }
  }
}
"""


class LinearClient:
    """Client for searching Linear issues."""

    def __init__(self, api_key: str) -> None:
        """Initialize with Linear API key."""
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search Linear issues."""
        results: list[SearchResult] = []

        try:
            with httpx.Client() as client:
                response = client.post(
                    GRAPHQL_URL,
                    headers=self.headers,
                    json={
                        "query": SEARCH_QUERY,
                        "variables": {"query": query, "first": limit},
                    },
                )
                response.raise_for_status()
                data = response.json()

            issues = data.get("data", {}).get("searchIssues", {}).get("nodes", [])

            for issue in issues[:limit]:
                description = issue.get("description", "") or ""
                assignee = issue.get("assignee")
                state = issue.get("state")

                results.append(
                    SearchResult(
                        source=SearchResultType.LINEAR,
                        title=f"[{issue.get('identifier')}] {issue.get('title', '')}",
                        url=issue.get("url", ""),
                        snippet=description[:200],
                        author=assignee.get("name") if assignee else None,
                        extra={"status": state.get("name")} if state else None,
                    )
                )
        except Exception as e:
            logger.error("linear_search_failed", error=str(e), query=query)

        return results
