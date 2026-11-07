from __future__ import annotations

import json

import pytest

from docs_agent.answer_engine import ground
from docs_agent.client import DocsMcpClient, DocsMcpError
from docs_agent.retrieval import retrieve


class FakeClient(DocsMcpClient):
    def __init__(self, body: str = ""):
        super().__init__(base_url="https://example.test/index.md")
        self.body = body

    def _get(self, url: str) -> str:
        return self.body


def test_successful_retrieval_and_citation_preservation():
    body = json.dumps({"answer": "Pacific is chain 1672.", "excerpts": ["Chain ID is 1672."], "sources": [{"title": "Pacific", "url": "https://docs.pharos.xyz/pacific.md"}]})
    result = retrieve(FakeClient(body), "What is mainnet?", "configure an app")
    assert result.error == ""
    grounded = ground(result.response)
    assert grounded.sufficient is True
    assert grounded.citations[0]["url"].endswith("pacific.md")


def test_empty_search_is_rejected():
    with pytest.raises(DocsMcpError, match="question"):
        FakeClient("{}").search("   ")


def test_malformed_response_is_rejected():
    result = retrieve(FakeClient("[]"), "unsupported?", "test")
    assert "non-object" in result.error


def test_missing_sources_is_explicitly_insufficient():
    response = FakeClient(json.dumps({"answer": "A plausible answer."})).search("question")
    grounded = ground(response)
    assert grounded.sufficient is False
    assert "insufficient" in grounded.interpretation


def test_markdown_sources_are_preserved():
    response = FakeClient("# Answer\nPacific is 1672.\n\n# Sources\n- [Pacific](https://docs.pharos.xyz/pacific.md)").search("question")
    assert response.sources == [{"title": "Pacific", "url": "https://docs.pharos.xyz/pacific.md"}]


def test_connection_failure_is_reported():
    class BrokenClient(FakeClient):
        def _get(self, url: str) -> str:
            raise DocsMcpError("offline")

    result = BrokenClient().check_connection()
    assert result["status"] == "Disconnected"
    assert result["error"] == "offline"


def test_query_history_model_can_retain_multiple_answers():
    first = ground(FakeClient(json.dumps({"answer": "one", "sources": ["https://docs.pharos.xyz/one"]})).search("one"))
    second = ground(FakeClient(json.dumps({"answer": "two", "sources": ["https://docs.pharos.xyz/two"]})).search("two"))
    history = [{"question": "one", "answer": first}, {"question": "two", "answer": second}]
    assert [item["answer"].answer for item in history] == ["one", "two"]