# PHAROS DOCS SEARCH

An isolated command-line assistant for searching the official Pharos Developer Docs. It preserves the original question, returned answer/excerpts, and source URLs. The optional Streamlit companion is an evaluation interface, not a replacement for the CLI.

## Arena task card

**Doc-Search CLI** is an **Easy / Developer Docs MCP** task worth **50 points**, with an optional **+50 points for a video**. The authoritative card requires:

1. A natural-language question as input.
2. A concise answer with links or references to source documentation sections.
3. Graceful handling of “no good answer found” without inventing one.
4. A README containing installation, usage, and three example queries with outputs.

Submission requires a proof link reviewers can open, such as an `ai.pharos.xyz` share link, explorer transaction hash, or deployed demo, plus a repository link. Arena submission requires GitHub sign-in.

## Verified integration

The official machine-readable docs index is [`https://docs.pharos.xyz/llms.txt`](https://docs.pharos.xyz/llms.txt). Its Agent Instructions define the live query interface:

```text
GET https://docs.pharos.xyz/index.md?ask=<question>&goal=<developer-goal>
```

The response is documented to contain a direct answer, relevant excerpts, and sources. The client accepts JSON responses and the Markdown fallback observed in the docs service. It never creates citations or relevance scores. No credentials are required for this public interface.

This is separate from the documented Pharos Chain MCP at [`https://mcp.pharos.xyz/mcp`](https://mcp.pharos.xyz/mcp), which uses Streamable HTTP and exposes chain tools such as `get_chain_info`, `eth_call`, `get_code`, `get_storage_at`, `get_logs`, and `send_raw_transaction`. The docs pages do not publish a named documentation-search MCP tool; therefore this project uses the official documented Docs HTTP query and does not claim an MCP tool call where none is specified.

## Install

```powershell
cd pharos-doc-search-cli
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional configuration is shown in `.env.example`; environment variables can be set directly in the shell.

## CLI

```powershell
.\.venv\Scripts\python.exe main.py doctor
.\.venv\Scripts\python.exe main.py search "What is the Pharos mainnet chain ID?"
.\.venv\Scripts\python.exe main.py search "How do I deploy a contract with Foundry?" --json
.\.venv\Scripts\python.exe main.py interactive
```

`doctor` probes the real docs query endpoint. `interactive` accepts multiple questions and exits on an empty line, `quit`, or `exit`. A failed request returns a clear error and nonzero status. Empty results remain successful retrievals with `status: empty`; they are not replaced with guessed answers.

### Example queries and outputs

```text
> python main.py search "What is the Pharos mainnet chain ID?"
Status: success
Answer: Pharos Pacific Mainnet's chain ID is 1672 (0x688).
Source: Pacific Mainnet https://docs.pharos.xyz/getting-started/network/pacific-mainnet.md

> python main.py search "How do I deploy a contract with Foundry?"
Status: success
Answer: [retrieved Foundry deployment guidance]
Source: Foundry https://docs.pharos.xyz/developer-guide/foundry.md

> python main.py search "What is the address of an undocumented protocol?"
Status: success
Answer: I can't identify an "undocumented protocol" from that description. The
retrieved answer offers a clearly labeled CCTP alternative instead of guessing.
Source: Circle CCTP https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/circle-cctp.md
```

All three examples were verified against the live service during development. Exact returned wording depends on the live documentation response. A genuinely empty response is represented as `status: empty` with “No documentation result was returned.”

## Streamlit

```powershell
.\.venv\Scripts\streamlit.exe run streamlit_app/app.py
```

The Explorer shows live status, examples, answer text, excerpts, clickable sources, and session history. It warns when a response has no source references and never presents demo data as live retrieval.

## Architecture

- `docs_search/client.py`: HTTP query transport, response validation, Markdown parsing, and citation deduplication.
- `docs_search/models.py`: immutable result and source models.
- `docs_search/retrieval.py`: error boundary shared by CLI and UI.
- `cli/`: argparse commands and text/JSON formatting.
- `streamlit_app/app.py`: optional live companion interface.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests mock the HTTP client and cover parsing, successful retrieval, empty results, timeout/connection errors, malformed responses, provenance, JSON output, interactive mode, doctor, and Streamlit wiring. Mocked tests are not live integration evidence. Run `doctor` and a real `search` separately when network access is available.

## Limitations and evidence status

The docs service may return JSON or Markdown, and its published instructions do not define a formal ranking score or a documentation-specific MCP tool schema. The CLI reports returned material without inventing ranking, completeness, or unsupported technical facts. Public GitHub publication, Streamlit Community Cloud deployment, screenshots, and Arena submission require external account/network access and are not claimed by this local project. The exact Arena card was verified at `https://pharos-agent-arena.vercel.app/tasks/doc-search-cli` on 2026-11-07.
