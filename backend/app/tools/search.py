"""Tavily-powered search tool for live web lookups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import anyio
from tavily import TavilyClient

from app.core.settings import get_settings


@dataclass(slots=True)
class SearchResult:
    title: str
    snippet: str
    url: str


class SearchTool:
    """Wrapper around the Tavily search API."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.tavily_api_key
        self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str, limit: int = 3) -> List[SearchResult]:
        response = await anyio.to_thread.run_sync(
            self._client.search,
            query,
            max_results=limit,
        )
        return [
            SearchResult(title=result["title"], snippet=result["content"], url=result["url"])
            for result in response.get("results", [])
        ]
