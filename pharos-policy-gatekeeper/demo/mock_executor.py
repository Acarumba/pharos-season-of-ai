from __future__ import annotations

from typing import Any, Mapping


class MockExecutor:
    """Records calls without signing, broadcasting, or touching a network."""

    def __init__(self) -> None:
        self.calls: list[Mapping[str, Any]] = []

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append(request)
        return {
            "simulated": True,
            "message": "Mock executor completed locally; no transaction was sent.",
        }