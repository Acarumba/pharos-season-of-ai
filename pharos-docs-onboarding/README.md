# PHAROS DOCS EXPLORER

An isolated Streamlit onboarding console for the Pharos Developer Docs agent interface. It asks the official documentation endpoint, preserves returned citations, separates documented facts from interpretation, and records query history in the current session.

## Verified task card

**Docs MCP Onboarding**, Developer Docs MCP, Easy, **50 points** with an optional **+50 video**. The authoritative card says: self-onboard into `ai.pharos.xyz` using only Developer Docs MCP, with no external docs, and log where it broke down.

Required evidence:

1. A step-by-step log of attempted work, exact Docs MCP questions, and answers.
2. At least three concrete gaps or breakdowns, each with the exact query.
3. A suggested fix for every gap.
4. The log ends with what was built or run.

Submission requires a proof link reviewers can open, such as a share link, transaction hash, or deployed demo, plus a repository link if code was written. Video is optional. See [`evaluation/onboarding_report.md`](evaluation/onboarding_report.md).

## Connection

The official machine-readable index is `https://docs.pharos.xyz/llms.txt`. Its agent instructions define the retrieval interface used here. The app's **Check connection** button probes the query endpoint itself, because some environments/CDN paths return 403 for a direct `llms.txt` fetch:

`GET https://docs.pharos.xyz/index.md?ask=<question>&goal=<developer-goal>`

The response contains a direct answer, relevant excerpts, and source references. This is intentionally kept separate from Pharos Chain MCP, whose documented Streamable HTTP endpoint is `https://mcp.pharos.xyz/mcp` and whose public tool set includes `get_chain_info`, `eth_call`, `get_code`, `estimate_gas`, and others. The explorer does not sign or broadcast transactions.

No credentials are required by the documented public Docs query. Configure overrides in `.env` or the environment using [`.env.example`](.env.example); never put credentials in the repository.

## Run

```powershell
cd pharos-docs-onboarding
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\streamlit.exe run app.py
```

For the current local review session, the app is running at `http://127.0.0.1:8511`. To reproduce that port explicitly:

```powershell
..\.venv\Scripts\streamlit.exe run app.py --server.address 127.0.0.1 --server.port 8511 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
```

Open the displayed local URL, use **Check connection**, and ask a question. The UI shows connection state, source, successful query count, last retrieval, excerpts, citations, history, and diagnostics.

Run mocked tests:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests
```

Mocked tests are not live MCP evidence. Live evidence is the official endpoint and source links recorded in the onboarding report.

## Limitations

- The service returns a Markdown answer in some responses and JSON in others; the client supports both formats but treats an answer without source links as insufficient implementation evidence.
- Query history is Streamlit session state and is not a permanent database.
- No deployed Streamlit Community Cloud URL or Arena submission was performed from this local workspace. Those require a public repository/deployment account and authenticated human submission.
- The app does not invent contract addresses, ABIs, RPCs, or transaction instructions when the docs omit them.