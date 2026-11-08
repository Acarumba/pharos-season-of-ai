# PHAROS ALERT WATCH

An on-chain alert bot for Pharos Mainnet that watches ERC-20 USDC Transfer logs and sends qualifying alerts to Telegram and/or email. The title-card task is **On-Chain Alert Bot** (50 points, plus 50 with video).

## Task coverage

- Configurable threshold, sender, recipient, and monitored-address rules.
- Enabled/disabled rules and multiple rules per event.
- Toggleable event-type allowlist; ERC-20 Transfer is the initial supported type.
- Telegram and SMTP email delivery with explicit delivered, failed, or unavailable status.
- Event details include rule, token, amount, sender, recipient, transaction hash, and block.
- Duplicate suppression by transaction hash plus log index plus rule.
- SQLite checkpoint and notification history.
- Temporary query errors leave the checkpoint unchanged for retry.
- Streamlit control panel with status, rules, live feed, notification history, and controls.

## Architecture

`app.py` owns the dashboard. `alert_engine/mcp_client.py` calls the Pharos Chain MCP endpoint. `decoder.py` parses ERC-20 logs. `rules.py` compares raw integer token amounts. `monitor.py` polls and deduplicates. `notifications.py` integrates Telegram and SMTP email. `storage.py` persists checkpoints, seen alerts, and notification attempts.

The initial token is `0xc879c018db60520f4355c26ed1a6d572cdac1815`. Its `decimals()` value was verified through `eth_call` as **6**. The target network is Pharos Mainnet, chain ID `1672`. Notifications retain the transaction hash; an explorer URL is omitted until an official Pharos explorer URL is verified.

## Setup

```powershell
cd pharos-onchain-alert-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` for Telegram. For email, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`; enter the recipient address in the sidebar. SMTP passwords are never shown in the UI or committed. Without a configured channel, monitoring still runs and records unavailable notification attempts.

## Run

```powershell
.\run_app.cmd
```

The launcher binds explicitly to `127.0.0.1:8514`, sets the project directory first, and avoids PowerShell execution-policy restrictions. To use another port, run `python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501` from this directory.

Add a rule, enable monitoring, and inspect the live feed. A threshold of `1000` means 1,000 USDC; comparisons are performed against integer base units.

## Test

```powershell
python -m pytest -q
```

The test suite uses mocked MCP and Telegram/SMTP responses. A live MCP smoke test is separate from these unit tests and must not be interpreted as a live alert or notification delivery.

## Deployment and limitations

Streamlit Community Cloud can host the dashboard, but it is not a reliable always-on worker: reruns, sleep, and ephemeral storage can interrupt polling and SQLite persistence. For continuous monitoring, run the monitor as a supervised process or scheduled worker with durable storage, and use Streamlit as the control panel. Configure the MCP endpoint and Telegram/SMTP credentials through deployment secrets.

The dashboard deliberately reports a transfer as a transfer. It does not label transfers as purchases, sales, deposits, or withdrawals without additional application evidence.

## Evidence

The verified chain smoke check retrieved Pharos chain ID `1672`, current block `22456404`, and USDC decimals `6` during development. Historical log retrieval, controlled unit tests, and live alerts must be reported separately; no Telegram or email delivery is claimed unless the provider confirms acceptance.
