from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st

from monitor.decoder import TRANSFER_SIGNATURE
from monitor.engine import MonitorEngine
from monitor.mcp_client import PharosMcpClient
from monitor.storage import EventStore


CONTRACT = os.getenv("PHAROS_CONTRACT", "0xc879c018db60520f4355c26ed1a6d572cdac1815")
DATA_PATH = Path(os.getenv("PHAROS_EVENT_WATCH_DB", "data/events.sqlite3"))

st.set_page_config(page_title="Pharos Event Watch", page_icon="◈", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --ink:#17221f; --muted:#6b7772; --line:#dbe4df; --mint:#b9f4d4; --coral:#ff765c; }
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; color: var(--ink); }
code, .mono { font-family: 'DM Mono', monospace; }
.watch-header { display:flex; justify-content:space-between; align-items:end; border-bottom:2px solid var(--ink); padding: 1.5rem 0 1rem; margin-bottom:1.5rem; }
.watch-title { font-size:2.1rem; font-weight:700; letter-spacing:0; }
.watch-subtitle { color:var(--muted); font-size:.9rem; margin-top:.25rem; }
.status { background:var(--mint); border-radius:999px; padding:.45rem .8rem; font-family:'DM Mono'; font-size:.75rem; }
.metric-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { font-family:'DM Mono'; font-size:1.35rem; margin-top:.25rem; }
.event-row { border-top:1px solid var(--line); padding:.75rem 0; }
</style>
""", unsafe_allow_html=True)


def get_engine(interval: float) -> MonitorEngine:
    engine = st.session_state.get("engine")
    if engine is None:
        client = PharosMcpClient(os.getenv("PHAROS_MCP_URL", "https://mcp.pharos.xyz/mcp"))
        store = EventStore(DATA_PATH)
        decimals = int(os.getenv("PHAROS_TOKEN_DECIMALS", "6"))
        engine = MonitorEngine(client, store, CONTRACT, decimals=decimals, poll_interval=interval)
        st.session_state.engine = engine
    engine.poll_interval = interval
    return engine


if "running" not in st.session_state:
    st.session_state.running = False

st.markdown('<div class="watch-header"><div><div class="watch-title">PHAROS EVENT WATCH</div><div class="watch-subtitle">Continuous ERC-20 Transfer monitor · Pharos Mainnet</div></div><div class="status">● MAINNET · CHAIN 1672</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Monitor configuration")
    contract = st.text_input("Contract address", CONTRACT)
    interval = st.slider("Polling interval (seconds)", 2, 60, 10)
    start_block = st.number_input("Start block", min_value=0, value=0, step=1, help="Use 0 to resume the persisted checkpoint.")
    st.caption(f"Event: {TRANSFER_SIGNATURE}")
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("Start", type="primary", width="stretch"):
            if not contract.startswith("0x") or len(contract) != 42:
                st.error("Enter a 20-byte contract address.")
            else:
                candidate = MonitorEngine(
                    PharosMcpClient(os.getenv("PHAROS_MCP_URL", "https://mcp.pharos.xyz/mcp")),
                    EventStore(DATA_PATH), contract, decimals=6, poll_interval=interval,
                )
                try:
                    candidate.start(start_block=start_block or None, resume=not bool(start_block))
                except Exception as exc:
                    candidate.store.close()
                    st.error(f"Could not connect to Pharos MCP: {exc}")
                else:
                    st.session_state.engine = candidate
                    st.session_state.running = True
                    st.rerun()
    with col_stop:
        if st.button("Stop", width="stretch"):
            st.session_state.running = False
            st.rerun()
    st.divider()
    st.caption("The dashboard refreshes once per second while enabled. The engine only queries the chain when the configured polling interval is due.")


@st.fragment(run_every=1)
def live_monitor() -> None:
    engine = get_engine(interval)
    if st.session_state.running:
        try:
            engine.poll_once()
        except Exception as exc:
            st.error(f"Poll failed; checkpoint was preserved. {exc}")

    events = engine.store.events(50)
    elapsed = (time.time() - engine.stats.started_at) if engine.stats.started_at else 0
    metrics = st.columns(5)
    values = [
        ("Events detected", str(engine.store.count())),
        ("Latest block", str(engine.cursor or "—")),
        ("Monitoring time", f"{int(elapsed)}s"),
        ("Last successful poll", time.strftime("%H:%M:%S", time.localtime(engine.stats.last_success)) if engine.stats.last_success else "—"),
        ("Connection", "LIVE" if not engine.stats.last_error else "ERROR"),
    ]
    for column, (label, value) in zip(metrics, values):
        with column:
            st.markdown(f'<div class="metric-label">{label}</div><div class="metric-value">{value}</div>', unsafe_allow_html=True)

    st.subheader("Live event feed")
    if not events:
        st.info("No Transfer events detected yet. Start monitoring to watch new blocks arrive.")
    else:
        st.dataframe(events, width="stretch", hide_index=True, column_config={
            "transaction_hash": st.column_config.TextColumn("Transaction hash"),
            "sender": st.column_config.TextColumn("Sender"),
            "recipient": st.column_config.TextColumn("Recipient"),
            "amount": st.column_config.TextColumn("USDC amount"),
        })

    with st.expander("Monitoring diagnostics"):
        st.write({"running": st.session_state.running, "cursor": engine.cursor,
                  "successful_polls": engine.stats.successful_polls,
                  "duplicates_suppressed": engine.stats.duplicates,
                  "last_error": engine.stats.last_error})


live_monitor()