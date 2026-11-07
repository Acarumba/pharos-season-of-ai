from __future__ import annotations

from dataclasses import dataclass

from .client import DocsResponse


@dataclass
class GroundedAnswer:
    answer: str
    facts: list[str]
    interpretation: str
    citations: list[dict[str, str]]
    sufficient: bool


def ground(response: DocsResponse) -> GroundedAnswer:
    answer = response.answer or "The documentation did not provide a direct answer."
    facts = response.excerpts[:5] or [answer]
    interpretation = (
        "Interpretation: use only the facts above; validate any missing deployment, ABI, or signing detail separately."
        if response.sources
        else "Interpretation: source references were not returned, so this answer is insufficient for implementation."
    )
    return GroundedAnswer(answer, facts, interpretation, response.sources, bool(response.sources))