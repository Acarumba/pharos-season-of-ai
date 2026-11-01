# Pharos Contract Inspector

Minimal read-only inspector for the Pharos Pacific Mainnet USDC contract.

## Network and contract

- Network: Pharos Pacific Mainnet
- Chain ID: `1672` (`0x688`)
- MCP endpoint: `https://mcp.pharos.xyz/mcp`
- Contract: `0xc879c018db60520f4355c26ed1a6d572cdac1815`
- Registry source: [Pharos Token Registry](https://docs.pharos.xyz/getting-started/token-registry.md)

## Architecture

`src/contract_inspector.py` connects through the public Pharos Chain MCP, pins a block, and calls the ERC-20 selectors for `name`, `symbol`, `totalSupply`, and `decimals`. `src/decode.py` validates ABI responses and applies decimal formatting. No signing, wallet, or transaction broadcast is used.

## Prerequisites

- Python 3.14 or newer
- Internet access to the public MCP endpoint

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run:

```powershell
python src\contract_inspector.py
```

The endpoint can be overridden with `PHAROS_MCP_URL`. No credentials or private keys are required.

## Verified live read

The Chain MCP returned non-empty bytecode and these reads at block `21813722`:

```text
Network: Pharos Pacific Mainnet (chain ID 1672)
Contract address: 0xc879c018db60520f4355c26ed1a6d572cdac1815
Block number: 21813722
Name: USDC
Symbol: USDC
Decimals: 6
Total supply: 3000000000.000006 USDC
Raw total supply: 3000000000000006
```

The displayed supply is `3000000000000006 / 10^6`.

## Tests

```powershell
python -m unittest discover -s test -v
```

The test matrix covers successful uint and string decoding, malformed responses, decimal conversion, and the zero-decimal edge case in the formatter. Live MCP reads are not mocked as evidence of success.

## Limitations

- The implementation depends on the public MCP endpoint and its rate limit.
- The installed MCP SDK's Streamable HTTP transport currently stalls in this environment after session startup; the endpoint itself is healthy and the live reads above were independently verified through Chain MCP.
- The inspector is intentionally read-only and does not provide transaction or proof-link generation.

## Walkthrough

1. Confirm the MCP endpoint is configured at `.vscode/mcp.json`.
2. Run the inspector.
3. Check the printed contract address and pinned block number.
4. Compare the raw and decimal-adjusted total supply.
5. Run the unit test command.

## Acceptance checklist

- [x] Four values requested from one deployed public contract through Chain MCP evidence.
- [x] Contract address and associated block displayed in the sample output.
- [x] Raw values formatted with token decimals and labels.
- [x] README includes contract, execution instructions, architecture, sample output, tests, and limitations.
- [ ] Repository URL: not available in the local workspace.
- [ ] Shareable Pharos proof link: not supported by the available MCP tools.