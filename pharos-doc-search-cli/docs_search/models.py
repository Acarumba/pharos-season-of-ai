from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    title: str
    url: str


@dataclass(frozen=True)
class SearchResult:
    query: str
    answer: str
    excerpts: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    status: str = "success"


@dataclass(frozen=True)
class SearchFailure:
    query: str
    error: str
    status: str = "error"
