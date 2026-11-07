from __future__ import annotations

from dataclasses import dataclass

from .client import DocsMcpClient, DocsMcpError, DocsResponse


@dataclass
class RetrievalResult:
    response: DocsResponse | None
    error: str = ""

    @property
    def has_citations(self) -> bool:
        return bool(self.response and self.response.sources)


def retrieve(client: DocsMcpClient, question: str, goal: str) -> RetrievalResult:
    try:
        return RetrievalResult(client.search(question, goal))
    except DocsMcpError as exc:
        return RetrievalResult(None, str(exc))