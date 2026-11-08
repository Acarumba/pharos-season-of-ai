# Pharos Event Watch

A Streamlit dashboard that continuously monitors Pharos Mainnet for ERC-20 `Transfer` events from a configured contract. The default contract is Pharos USDC:

`0xc879c018db60520f4355c26ed1a6d572cdac1815`

## Verified network configuration

- Network: Pharos Mainnet
- Chain ID: `1672` (`0x688`)
- MCP endpoint: `https://mcp.pharos.xyz/mcp`
- Event: `Transfer(address,address,uint256)`
- Topic0: `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- USDC decimals: `6`, verified with the on-chain `decimals()` call

A live MCP query was performed during implementation and returned genuine Transfer logs from the configured contract, including block `0x1546de3`. This is historical discovery evidence, not a claim that the event was caught after the dashboard was started. Run the application and inspect the live feed to perform a fresh verification.

## Architecture

- `app.py`: Streamlit presentation, controls, one-session live refresh loop
- `monitor/mcp_client.py`: official MCP Python SDK over streamable HTTP
- `monitor/engine.py`: incremental polling, 1,000-block paging, error recovery
- `monitor/decoder.py`: Keccak topic generation and defensive ABI log decoding
- `monitor/storage.py`: SQLite cursor and event persistence
- `tests/`: decoder, empty-result, incremental polling, failure recovery, and restart tests

The page fragment refreshes once per second while enabled. The engine only calls Pharos when the configured polling interval is due. This avoids starting background threads or duplicate monitor loops during Streamlit reruns.

## Installation and local run

```powershell
cd pharos-event-watch
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Open the URL printed by Streamlit, usually `http://localhost:8501`.

The Start button begins a fresh monitoring session: it clears the previous event feed and persisted cursor before initializing. The Stop button pauses polling without deleting the current SQLite checkpoint. A start block of `0` begins at the current chain head; a positive start block begins at that block. The default database is `data/events.sqlite3`, which is ignored by git. If the application restarts without starting a new session, the engine can resume its persisted cursor.

## Configuration

Optional environment variables are documented in `.env.example`:

- `PHAROS_MCP_URL`
- `PHAROS_CONTRACT`
- `PHAROS_EVENT_WATCH_DB`
- `PHAROS_TOKEN_DECIMALS`

The app validates the contract shape before starting. The event signature and topic are fixed to the ERC-20 Transfer event in this implementation.

## Polling and persistence

Each cycle reads the latest block, then queries `[cursor + 1, latest]` in inclusive windows of at most 1,000 blocks. The cursor is committed after each successful window. A failed query records the error and does not advance the failed window. Events use `transactionHash + logIndex` as the SQLite primary key, so repeats are suppressed across polling cycles and application restarts.

This is polling-based near-real-time monitoring, not a websocket subscription. Delivery latency is approximately the configured polling interval plus request time. The implementation does not currently reconcile chain reorganizations; a reorg-aware deployment should retain a confirmation depth and reconcile recent blocks.

## Tests

```powershell
py -m pytest -q
```

Tests use fake MCP clients and do not replace live-chain verification. They cover Keccak topic generation, indexed address decoding, unit conversion, malformed logs, empty ranges, incremental ranges, failed queries, and persisted cursor restart.

## Streamlit Community Cloud

1. Push the repository to GitHub.
2. Create a Streamlit Community Cloud app targeting `pharos-event-watch/app.py`.
3. Set the app working directory to `pharos-event-watch` if prompted.
4. Add any required values as Streamlit secrets or environment variables. No credentials are required for the public Pharos MCP endpoint currently used here.
5. Deploy and verify that the app can reach `https://mcp.pharos.xyz/mcp`.

Deployment has not been claimed or performed by this repository. A deployed app should use a persistent storage strategy if its filesystem is not durable; local SQLite is appropriate for local review but may reset on hosted restarts.

## Known limitations

- Polling latency depends on the selected interval and MCP response time.
- Timestamp enrichment makes an additional block request per distinct block.
- The current SQLite file is local to the running instance.
- Reorganizations are not automatically reconciled.
- The dashboard displays historical discoveries and newly caught events in one persisted feed; the engine itself does not label their origin.
