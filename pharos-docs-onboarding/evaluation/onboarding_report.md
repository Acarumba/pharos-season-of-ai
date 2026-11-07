# Pharos Docs MCP Onboarding Report

Date: 2026-11-07

## Scope and evidence boundary

The Agent Arena card was opened at [Docs MCP Onboarding](https://pharos-agent-arena.vercel.app/tasks/docs-mcp-onboarding). It is an Easy, 50-point task with optional +50 video. The report follows its four requirements and keeps live documentation evidence separate from mocked application tests.

The official documentation index identifies the agent query mechanism at [llms.txt](https://docs.pharos.xyz/llms.txt). The live query form is `https://docs.pharos.xyz/index.md?ask=...&goal=...`. The official [Pharos MCP page](https://docs.pharos.xyz/tooling-and-infrastructure/mcp.md) separately documents Chain MCP at `https://mcp.pharos.xyz/mcp`, public authentication, a 120 requests/minute limit, and tools including `get_chain_info`, `get_block`, `get_gas_price`, `eth_call`, `get_code`, `estimate_gas`, `get_logs`, and `send_raw_transaction`. The explorer uses the Docs query interface, not the Chain MCP endpoint.

## Step-by-step log

1. Asked: “What are the Pharos mainnet and testnet chain IDs and RPC endpoints?” The official query response identified Pacific Mainnet as chain `1672` with `https://rpc.pharos.xyz`, and Atlantic Testnet as `688689` with `https://atlantic.dplabs-internal.com`. It cited the Pacific and Atlantic network pages. **Accurate and complete for the question.**
2. Asked: “How do I configure a Pharos MCP client and what authentication does it require?” The MCP page documented the Streamable HTTP endpoint, a JSON client configuration, no API key, and the public health check. **Accurate and complete.**
3. Asked: “What tools does Pharos MCP expose for reading contract state?” The response listed `eth_call`, `get_code`, `get_storage_at`, and `get_logs`, with the JSON-RPC mapping and log-range limitation. **Accurate and complete.**
4. Asked: “How do I deploy a smart contract on Pharos using Foundry?” The docs index led to the Foundry guide and deployment workflow. **Partially complete:** the guide is useful, but a single answer did not establish a complete, independently reproducible deployment proof for this run.
5. Asked: “How can I read a contract’s state without sending a transaction?” The docs distinguished read-only `eth_call` and related contract tools from broadcasting. **Accurate; contract-specific address/ABI details remain query-dependent.**
6. Asked: “How are Pharos transactions signed and broadcast?” The answer documented local signing and passing signed bytes to `send_raw_transaction`; private keys are not sent to MCP. **Accurate and complete for the signing boundary.**
7. Asked: “What is the Pharos gas model and native gas token?” The response linked the gas model and network pages. **Partially complete:** gas model concepts were covered, but exact operational cost expectations require current chain data.
8. Asked: “How do I use the Pharos Skill Engine?” The answer linked the Skill Engine guide and described callable packaged actions. **Partially correct:** the docs did not provide one end-to-end local execution that could be verified solely from this workspace.
9. Asked: “What is the relationship between ai.pharos.xyz, Chain MCP, and Developer Docs?” The response identified the AI workspace, Chain MCP, and machine-readable docs as separate resources. **Accurate; ownership and versioning between surfaces are not explicit.**
10. Asked: “What should an agent do when the documentation does not specify a contract address or ABI?” The docs provide safe MCP/tool boundaries, but no universal fallback policy. **Documentation cannot fully answer this; the explorer therefore reports insufficiency and does not invent deployment data.**

## Breakdown log

### Gap 1: Docs MCP naming and transport are ambiguous

Exact query: “What is the official Developer Docs MCP endpoint, tool list, and authentication requirement?”

The official AI page calls the resource “Docs MCP,” while the machine-readable docs expose the concrete `index.md?ask=...&goal=...` HTTP query. The Chain MCP page documents a separate MCP endpoint and tool schemas, but no equivalent named tool schema for the Docs query. **Classification: confusing / partially documented.**

Suggested fix: publish a dedicated Docs MCP page with the canonical endpoint, transport, request and response JSON schema, citation schema, rate limits, and one request/response example. State explicitly whether the HTTP query is the supported Docs MCP transport or only an agent convenience interface.

### Gap 2: Deployment guidance does not close the proof loop

Exact query: “Give me a complete Pharos Foundry deployment command sequence, including network configuration, deploy command, and how to verify the deployed address.”

The docs index links to Foundry material, but the onboarding answer does not guarantee a single reproducible sequence with a verification command and expected output. **Classification: missing / incomplete.**

Suggested fix: add a minimal copy-paste deployment tutorial with `foundry.toml`, RPC/chain configuration, deploy command, explorer verification, and an explicit warning about private-key handling.

### Gap 3: Unsupported contract facts have no explicit fallback policy

Exact query: “If the docs do not contain a contract address or ABI for a requested Pharos integration, what should an agent do?”

The material explains Chain MCP capabilities but does not state a clear rule to stop, ask for a verified source, or label an address as unknown. **Classification: missing.**

Suggested fix: add an “insufficient evidence” policy: never infer addresses or ABIs; return the missing fields; identify the canonical source to consult; and provide a read-only verification path once an address is supplied.

## Evaluation summary

| Question | Accuracy | Completeness | Citations | Improvement |
|---|---|---|---|---|
| Networks and RPCs | Correct | Complete | Sufficient | Keep network pages current |
| MCP setup/auth | Correct | Complete | Sufficient | Add Docs-specific schema |
| Contract-read tools | Correct | Complete | Sufficient | Add examples per tool |
| Foundry deployment | Partial | Partial | Sufficient | Add copy-paste proof loop |
| Read contract state | Correct | Partial | Sufficient | Add ABI/address examples |
| Sign and broadcast | Correct | Complete | Sufficient | Add signer safety checklist |
| Gas model | Partial | Partial | Sufficient | Add current-data examples |
| Skill Engine | Partial | Partial | Sufficient | Add reproducible local run |
| AI/Chain/Docs relationship | Correct | Partial | Sufficient | Clarify product boundaries |
| Missing ABI/address behavior | Unsupported | Incomplete | Insufficient | Publish explicit stop policy |

## What was built and run

The isolated [`pharos-docs-onboarding`](../README.md) package contains the Streamlit explorer, a stdlib Docs client, retrieval/error handling, grounded-answer formatting, citation preservation, a 10-question evaluation set, and mocked tests. The UI is designed to show live connection state and source links. Automated coverage includes connection failures, successful retrieval, empty questions, malformed responses, missing citations, Markdown citations, grounding, and query history. No transaction was signed or broadcast.

The local proof link is the repository path; a public GitHub URL and deployed Streamlit URL remain outstanding human/deployment actions. Arena submission requires GitHub sign-in and was not claimed here.