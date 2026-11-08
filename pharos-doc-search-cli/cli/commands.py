from __future__ import annotations

import argparse
import json
from typing import Sequence

from docs_search.client import DocsClient
from docs_search.retrieval import retrieve

from .formatter import format_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pharos-doc-search", description="Search the official Pharos Developer Docs.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    search = subparsers.add_parser("search", help="Search documentation.")
    search.add_argument("query")
    search.add_argument("--goal", default="help a developer use Pharos")
    search.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit machine-readable JSON.")
    interactive = subparsers.add_parser("interactive", help="Search repeatedly until exit.")
    interactive.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit machine-readable JSON.")
    doctor = subparsers.add_parser("doctor", help="Check the documentation query endpoint.")
    doctor.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="Emit machine-readable JSON.")
    return parser


def run(argv: Sequence[str] | None = None, client: DocsClient | None = None, input_fn=input, output_fn=print) -> int:
    args = build_parser().parse_args(argv)
    client = client or DocsClient(timeout=args.timeout)
    if args.command == "doctor":
        result = client.check_connection()
        output_fn(json.dumps(result, indent=2) if args.json else "\n".join(f"{key}: {value}" for key, value in result.items()))
        return 0 if result["status"] == "Connected" else 1
    if args.command == "search":
        result = retrieve(client, args.query, args.goal)
        output_fn(format_result(result, args.json))
        return 0 if result.status != "error" else 1
    while True:
        try:
            query = input_fn("docs> ").strip()
        except EOFError:
            break
        if query.lower() in {"", "exit", "quit"}:
            break
        result = retrieve(client, query)
        output_fn(format_result(result, args.json))
    return 0
