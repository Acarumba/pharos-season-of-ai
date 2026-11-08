from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import SearchResult, Source

DEFAULT_DOCS_URL = "https://docs.pharos.xyz/index.md"
DEFAULT_INDEX_URL = "https://docs.pharos.xyz/llms.txt"


class DocsSearchError(RuntimeError):
    """A network, protocol, or response validation error."""


class DocsClient:
    def __init__(self, base_url: str | None = None, timeout: float = 20.0) -> None:
        self.base_url = (base_url or os.getenv("PHAROS_DOCS_URL", DEFAULT_DOCS_URL)).rstrip("?")
        self.index_url = os.getenv("PHAROS_DOCS_INDEX_URL", DEFAULT_INDEX_URL)
        self.timeout = timeout
        self.last_error = ""
        self.last_status = "Not checked"
        self.request_count = 0

    def _get(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain, text/markdown",
                "User-Agent": "PharosDocsSearchCLI/1.0",
                "Referer": "https://docs.pharos.xyz/",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise DocsSearchError(f"Documentation service request failed: {exc}") from exc

    def check_connection(self) -> dict[str, str]:
        try:
            body = self._get(self._query_url("What is Pharos?", "verify documentation connectivity"))
            if not body.strip():
                raise DocsSearchError("Documentation query returned an empty response")
            self.last_status = "Connected"
            self.last_error = ""
            return {"status": self.last_status, "endpoint": self.base_url}
        except DocsSearchError as exc:
            self.last_status = "Disconnected"
            self.last_error = str(exc)
            return {"status": self.last_status, "endpoint": self.base_url, "error": self.last_error}

    def search(self, query: str, goal: str = "help a developer use Pharos") -> SearchResult:
        original_query = query
        query = query.strip()
        if not query:
            raise DocsSearchError("Search query cannot be empty")
        self.request_count += 1
        body = self._get(self._query_url(query, goal))
        try:
            payload: Any = json.loads(body)
        except json.JSONDecodeError:
            payload = {"answer": self._markdown_answer(body), "sources": self._markdown_sources(body)}
        if not isinstance(payload, dict):
            raise DocsSearchError("Documentation service returned a non-object response")
        answer = self._markdown_answer(str(payload.get("answer") or payload.get("response") or payload.get("content") or ""))
        excerpts = self._excerpts(payload.get("excerpts") or payload.get("relevant_excerpts") or [])
        sources = self._sources(payload.get("sources") or payload.get("references") or [])
        if not answer and not excerpts:
            self.last_status = "No results"
            self.last_error = ""
            return SearchResult(original_query, "", excerpts, sources, payload, "empty")
        self.last_status = "Success"
        self.last_error = ""
        return SearchResult(original_query, answer, excerpts, sources, payload)

    def _query_url(self, query: str, goal: str) -> str:
        return f"{self.base_url}?{urlencode({'ask': query, 'goal': goal})}"

    @staticmethod
    def _sources(value: Any) -> list[Source]:
        if not isinstance(value, list):
            return []
        sources: list[Source] = []
        seen: set[str] = set()
        for item in value:
            if isinstance(item, str):
                url, title = item.strip(), item.strip()
            elif isinstance(item, dict):
                url = str(item.get("url") or item.get("source") or "").strip()
                title = str(item.get("title") or item.get("name") or url).strip()
            else:
                continue
            if url and url not in seen:
                seen.add(url)
                sources.append(Source(title, url))
        return sources

    @staticmethod
    def _excerpts(value: Any) -> list[str]:
        if not isinstance(value, list):
            return [str(value).strip()] if value else []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _markdown_sources(body: str) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        in_sources = False
        for line in body.splitlines():
            if line.strip().lower().startswith("# sources"):
                in_sources = True
                continue
            if in_sources:
                match = re.search(r"\[([^]]+)\]\((https?://[^)]+)\)", line)
                if match:
                    sources.append({"title": match.group(1), "url": match.group(2)})
        return sources

    @staticmethod
    def _markdown_answer(body: str) -> str:
        sections = re.split(r"^#\s+(?:Suggested Follow-up Questions|Sources)\s*$", body, flags=re.MULTILINE | re.IGNORECASE)
        return sections[0].strip()
