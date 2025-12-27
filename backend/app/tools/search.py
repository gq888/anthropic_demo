"""Tavily-powered search tool for live web lookups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import anyio
import functools
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
        if not query or not query.strip():
            return []
        call = functools.partial(self._client.search, query=query, max_results=limit)
        response = await anyio.to_thread.run_sync(call)
        results = response.get("results", []) if response else []
        if not results:
            return []
        return [
            SearchResult(title=result["title"], snippet=result.get("content", ""), url=result["url"])
            for result in results
        ]
