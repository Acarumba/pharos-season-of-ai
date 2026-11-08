from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st

from alert_engine.decoder import format_amount
from alert_engine.mcp_client import MCPError, PharosMCPClient
from alert_engine.monitor import Monitor
from alert_engine.notifications import NotificationRouter
from alert_engine.rules import AlertRule, parse_threshold, validate_address, validate_email
from alert_engine.storage import Storage

st.set_page_config(page_title="PHAROS ALERT WATCH", page_icon="◈", layout="wide")
st.markdown("""
<style>
:root { --ink:#10212b; --cyan:#0a8f9c; --coral:#e36b52; --paper:#f4f1e8; }
.stApp { background:var(--paper); color:var(--ink); }
.block-container { max-width:1200px; padding-top:2rem; }
.hero { border-bottom:2px solid var(--ink); padding:1rem 0 1.5rem; margin-bottom:1.5rem; }
.hero h1 { font-family:Georgia,serif; font-size:3.3rem; letter-spacing:0; margin:0; color:var(--ink); }
.hero p { font-size:1.05rem; color:#49616a; margin:.5rem 0 0; }
.metric { background:#fffdf7; border:1px solid #c9d1ce; padding:1rem; min-height:104px; }
.metric small { color:var(--cyan); text-transform:uppercase; letter-spacing:.08em; }
.metric strong { display:block; font-size:1.8rem; margin-top:.4rem; }
[data-testid="stSidebar"] { background:#17343b; }
[data-testid="stSidebar"] * { color:#f4f1e8 !important; }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.getenv("ALERT_BOT_DB", str(Path(__file__).with_name("alert_bot.sqlite3")))
TOKEN = "0xc879c018db60520f4355c26ed1a6d572cdac1815"

if "storage" not in st.session_state:
    st.session_state.storage = Storage(DB_PATH)
if "rules" not in st.session_state:
    st.session_state.rules = []
if "events" not in st.session_state:
    st.session_state.events = []
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

storage: Storage = st.session_state.storage
client = PharosMCPClient(os.getenv("PHAROS_MCP_ENDPOINT", "https://mcp.pharos.xyz/mcp"))

st.markdown('<div class="hero"><h1>PHAROS ALERT WATCH</h1><p>On-chain transfer signals, watched with restraint.</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Monitoring controls")
    interval = st.number_input("Polling interval (seconds)", min_value=5, value=15, step=5)
    enabled_event_types = set(st.multiselect("Event types", ["transfer"], default=["transfer"], help="Only selected event types are queried and alerted."))
    start = st.button("Start monitoring", type="primary", use_container_width=True)
    stop = st.button("Stop monitoring", use_container_width=True)
    if start: st.session_state.monitoring = True
    if stop: st.session_state.monitoring = False
    st.caption(f"Status: {'RUNNING' if st.session_state.monitoring else 'STOPPED'}")
    st.divider()
    st.subheader("Telegram")
    st.write("Configured" if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID") else "Not configured")
    st.subheader("Email notifications")
    email_recipient = st.text_input("Recipient email", value=st.session_state.get("email_recipient", ""), placeholder="you@example.com")
    try:
        st.session_state.email_recipient = validate_email(email_recipient) if email_recipient else ""
    except ValueError as exc:
        st.session_state.email_recipient = ""
        st.caption(str(exc))
    email_configured = bool(email_recipient.strip() and os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", "")))
    st.write("Configured" if email_configured else "Not configured")

notifier = NotificationRouter(storage, st.session_state.get("email_recipient", ""))

with st.sidebar:
    if st.button("Test Telegram", disabled=not notifier.telegram.configured):
        result = notifier.telegram.test_notification()
        st.info(f"Telegram {result.status}: {result.detail}")
    if st.button("Test email", disabled=notifier.email.configured):
        result = notifier.email.test_notification()
        st.info(f"Email {result.status}: {result.detail}")

try:
    chain = client.chain_info()
    chain_status = "Connected"
    block = client.block_number()
except Exception as exc:
    chain_status = "Unavailable"
    block = storage.get_checkpoint("transfer", 0)
    st.warning(f"Chain connection: {exc}")

cols = st.columns(5)
metrics = [("Monitoring", "LIVE" if st.session_state.monitoring else "IDLE"), ("Chain", chain_status), ("Events detected", len(st.session_state.events)), ("Alerts triggered", len(st.session_state.events)), ("Latest block", block)]
for col, (label, value) in zip(cols, metrics):
    col.markdown(f'<div class="metric"><small>{label}</small><strong>{value}</strong></div>', unsafe_allow_html=True)

st.subheader("Rule management")
with st.form("rule_form"):
    name = st.text_input("Rule name", placeholder="Treasury transfer")
    threshold = st.text_input("Minimum USDC amount", placeholder="1000")
    sender = st.text_input("Sender address (optional)")
    recipient = st.text_input("Recipient address (optional)")
    monitored = st.text_input("Monitored address (optional)")
    enabled = st.checkbox("Enabled", value=True)
    submitted = st.form_submit_button("Add rule")
    if submitted:
        try:
            if not name.strip(): raise ValueError("rule name is required")
            rule = AlertRule(name.strip(), enabled, parse_threshold(threshold or "0", 6) if threshold else None, validate_address(sender) if sender else None, validate_address(recipient) if recipient else None, validate_address(monitored) if monitored else None)
            st.session_state.rules.append(rule)
            st.success("Rule added")
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.rules:
    st.dataframe([{"name": r.name, "enabled": r.enabled, "threshold_raw": r.threshold_raw, "sender": r.sender, "recipient": r.recipient, "monitored": r.monitored_address} for r in st.session_state.rules], use_container_width=True, hide_index=True)
else:
    st.info("No rules configured yet.")

if st.session_state.monitoring and st.session_state.rules:
    @st.fragment(run_every=f"{interval}s")
    def run_monitor() -> None:
        try:
            monitor = Monitor(client, storage, TOKEN, st.session_state.rules, enabled_event_types=enabled_event_types)
            alerts = monitor.poll_once()
            for alert in alerts:
                st.session_state.events.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "rule": alert.rule.name, "amount": format_amount(alert.event.amount_raw, monitor.decimals), "sender": alert.event.sender, "recipient": alert.event.recipient, "tx": alert.event.transaction_hash, "block": alert.event.block_number, "notification": notifier.send(alert.event, alert.rule, monitor.decimals)})
        except MCPError as exc:
            st.error(f"Poll failed; checkpoint retained: {exc}")

    run_monitor()

st.subheader("Live alert feed")
if st.session_state.events:
    st.dataframe(st.session_state.events[-50:][::-1], use_container_width=True, hide_index=True)
else:
    st.info("No qualifying alerts yet. Historical events and live alerts are kept distinct.")

st.subheader("Notification history")
rows = [dict(row) for row in storage.recent_notifications()]
st.dataframe(rows, use_container_width=True, hide_index=True) if rows else st.caption("No notifications recorded.")
