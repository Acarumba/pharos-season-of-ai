from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_DOCS_URL = "https://docs.pharos.xyz/index.md"
DEFAULT_INDEX_URL = "https://docs.pharos.xyz/llms.txt"


class DocsMcpError(RuntimeError):
    """Raised when the documented Docs query cannot be completed or parsed."""


@dataclass
class DocsResponse:
    question: str
    answer: str
    sources: list[dict[str, str]]
    excerpts: list[str]
    raw: dict[str, Any]
    status: str = "success"


class DocsMcpClient:
    """Small stdlib client for the public Pharos agent documentation endpoint."""

    def __init__(self, base_url: str | None = None, timeout: float = 20.0) -> None:
        self.base_url = (base_url or os.getenv("PHAROS_DOCS_URL", DEFAULT_DOCS_URL)).rstrip("?")
        self.index_url = os.getenv("PHAROS_DOCS_INDEX_URL", DEFAULT_INDEX_URL)
        self.timeout = timeout
        self.last_status = "Not checked"
        self.last_error = ""
        self.request_count = 0

    def _get(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "Accept": "text/plain, text/markdown, application/json",
                "User-Agent": "Mozilla/5.0 (compatible; PharosDocsExplorer/1.0)",
                "Referer": "https://docs.pharos.xyz/",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise DocsMcpError(f"Documentation service request failed: {exc}") from exc

    def check_connection(self) -> dict[str, str]:
        try:
            probe_url = f"{self.base_url}?{urlencode({'ask': 'What is Pharos?', 'goal': 'verify the documentation service connection'})}"
            body = self._get(probe_url)
            if not body.strip():
                raise DocsMcpError("Documentation query returned an empty response")
            self.last_status = "Connected"
            self.last_error = ""
            return {"status": self.last_status, "endpoint": self.base_url}
        except DocsMcpError as exc:
            self.last_status = "Disconnected"
            self.last_error = str(exc)
            return {"status": self.last_status, "endpoint": self.base_url, "error": self.last_error}

    def search(self, question: str, goal: str = "onboard a Pharos developer") -> DocsResponse:
        question = question.strip()
        if not question:
            raise DocsMcpError("Enter a documentation question first")
        url = f"{self.base_url}?{urlencode({'ask': question, 'goal': goal})}"
        self.request_count += 1
        body = self._get(url)
        try:
            payload: Any = json.loads(body)
        except json.JSONDecodeError:
            payload = {"answer": body, "sources": self._markdown_sources(body)}
        if not isinstance(payload, dict):
            raise DocsMcpError("Documentation service returned a non-object response")
        answer = str(payload.get("answer") or payload.get("response") or payload.get("content") or "").strip()
        sources = self._sources(payload.get("sources") or payload.get("references") or [])
        excerpts = self._excerpts(payload.get("excerpts") or payload.get("relevant_excerpts") or [])
        if not answer and not excerpts:
            raise DocsMcpError("Documentation service returned no answer or excerpts")
        self.last_status = "Success"
        self.last_error = ""
        return DocsResponse(question, answer, sources, excerpts, payload)

    @staticmethod
    def _sources(value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            if isinstance(item, str):
                result.append({"title": item, "url": item})
            elif isinstance(item, dict):
                url = str(item.get("url") or item.get("source") or "").strip()
                title = str(item.get("title") or item.get("name") or url).strip()
                if url:
                    result.append({"title": title, "url": url})
        return result

    @staticmethod
    def _excerpts(value: Any) -> list[str]:
        if not isinstance(value, list):
            return [str(value)] if value else []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _markdown_sources(body: str) -> list[dict[str, str]]:
        sources = []
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