from __future__ import annotations

import json

from cli.commands import build_parser, run
from docs_search.client import DocsClient, DocsSearchError


class FakeClient(DocsClient):
    def __init__(self, body: str = ""):
        super().__init__(base_url="https://example.test/index.md")
        self.body = body

    def _get(self, url: str) -> str:
        return self.body


def test_argument_parsing():
    args = build_parser().parse_args(["search", "What is Pharos?", "--goal", "learn"])
    assert args.command == "search"
    assert args.query == "What is Pharos?"


def test_successful_retrieval_and_sources():
    client = FakeClient(json.dumps({"answer": "Pacific is 1672.", "excerpts": ["Chain ID is 1672."], "sources": [{"title": "Pacific", "url": "https://docs.pharos.xyz/pacific.md"}]}))
    output: list[str] = []
    assert run(["search", "What is mainnet?"], client, output_fn=output.append) == 0
    assert "pacific.md" in output[0]


def test_empty_results_are_explicit():
    output: list[str] = []
    assert run(["search", "unsupported"], FakeClient("{}"), output_fn=output.append) == 0
    assert "No documentation result" in output[0]


def test_connection_failure_is_graceful():
    class Broken(FakeClient):
        def _get(self, url: str) -> str:
            raise DocsSearchError("offline")

    output: list[str] = []
    assert run(["search", "question"], Broken(), output_fn=output.append) == 1
    assert "offline" in output[0]


def test_timeout_failure_is_graceful():
    class TimedOut(FakeClient):
        def _get(self, url: str) -> str:
            raise DocsSearchError("timed out")

    output: list[str] = []
    assert run(["search", "question"], TimedOut(), output_fn=output.append) == 1
    assert "timed out" in output[0]


def test_malformed_response_is_rejected():
    output: list[str] = []
    assert run(["search", "question"], FakeClient("[]"), output_fn=output.append) == 1
    assert "non-object" in output[0]


def test_json_output_is_valid_and_preserves_query():
    output: list[str] = []
    assert run(["--json", "search", "chain id"], FakeClient(json.dumps({"answer": "1672", "sources": ["https://docs.pharos.xyz/network.md", "https://docs.pharos.xyz/network.md"]})), output_fn=output.append) == 0
    payload = json.loads(output[0])
    assert payload["query"] == "chain id"
    assert len(payload["sources"]) == 1


def test_json_markdown_answer_excludes_service_sections():
    body = {"answer": "# Answer\nUse the docs.\n\n# Sources\n- [Docs](https://docs.pharos.xyz/docs.md)", "sources": [{"title": "Docs", "url": "https://docs.pharos.xyz/docs.md"}]}
    result = FakeClient(json.dumps(body)).search("question")
    assert result.answer == "# Answer\nUse the docs."


def test_markdown_source_attribution():
    client = FakeClient("# Answer\nPacific is 1672.\n\n# Sources\n- [Pacific](https://docs.pharos.xyz/pacific.md)")
    output: list[str] = []
    run(["search", "question"], client, output_fn=output.append)
    assert "Pacific" in output[0]


def test_markdown_answer_excludes_followups_and_source_section():
    body = "# Answer\nPacific is 1672.\n\n# Suggested Follow-up Questions\n- Verify it\n\n# Sources\n- [Pacific](https://docs.pharos.xyz/pacific.md)"
    result = FakeClient(body).search("question")
    assert result.answer == "# Answer\nPacific is 1672."
    assert result.sources[0].url.endswith("pacific.md")


def test_interactive_supports_multiple_queries():
    client = FakeClient(json.dumps({"answer": "answer", "sources": []}))
    entered = iter(["first", "second", "quit"])
    output: list[str] = []
    assert run(["interactive"], client, input_fn=lambda _: next(entered), output_fn=output.append) == 0
    assert len(output) == 2


def test_doctor_reports_success():
    output: list[str] = []
    assert run(["doctor"], FakeClient("ok"), output_fn=output.append) == 0
    assert "Connected" in output[0]
