from __future__ import annotations

import json
from typing import Any

from docs_search.retrieval import result_dict
from docs_search.models import SearchFailure, SearchResult


def format_result(result: SearchResult | SearchFailure, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(result_dict(result), indent=2)
    if isinstance(result, SearchFailure):
        return f"Query: {result.query}\nStatus: ERROR\nError: {result.error}"
    lines = [f"Query: {result.query}", f"Status: {result.status}"]
    if result.answer:
        lines += ["\nAnswer (from retrieved documentation):", result.answer]
    if result.excerpts:
        lines.append("\nRelevant excerpts:")
        lines.extend(f"- {excerpt}" for excerpt in result.excerpts)
    lines.append("\nSources:")
    lines.extend(f"- {source.title}: {source.url}" for source in result.sources)
    if not result.answer and not result.excerpts:
        lines.append("No documentation result was returned.")
    return "\n".join(lines)
