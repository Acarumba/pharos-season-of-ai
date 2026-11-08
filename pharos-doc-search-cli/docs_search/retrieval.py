from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .client import DocsClient, DocsSearchError
from .models import SearchFailure, SearchResult


def retrieve(client: DocsClient, query: str, goal: str = "help a developer use Pharos") -> SearchResult | SearchFailure:
    try:
        return client.search(query, goal)
    except DocsSearchError as exc:
        return SearchFailure(query, str(exc))


def result_dict(result: SearchResult | SearchFailure) -> dict[str, Any]:
    data = asdict(result)
    if isinstance(result, SearchResult):
        data["sources"] = [asdict(source) for source in result.sources]
    return data
