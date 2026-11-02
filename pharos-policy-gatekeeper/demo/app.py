from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
import sys

import streamlit as st

PACKAGE_DIR = Path(__file__).resolve().parents[1]
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from demo.demo_logic import (
    ADDRESS,
    CONTRACT,
    RULES,
    SCENARIOS,
    load_policy,
    rule_statuses,
    run_request,
    run_scenario,
)


st.set_page_config(page_title="Policy Gatekeeper | Pharos", page_icon="PG", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    :root { --ink:#17232b; --muted:#6d7b80; --paper:#f5f7f4; --panel:#ffffff;
            --line:#dce5e2; --teal:#087f76; --teal-soft:#dff3ee; --coral:#df5c48;
            --coral-soft:#fbe7e2; --gold:#bd7a17; }
    .stApp { background:var(--paper); color:var(--ink); }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:#172a2d; border-right:0; }
    [data-testid="stSidebar"] * { color:#e7f2ef; }
    [data-testid="stSidebar"] .stCaption { color:#a9c2bd; }
    h1,h2,h3,p,div,span,button { font-family:'Space Grotesk', sans-serif; }
    h1 { letter-spacing:-.04em; font-size:clamp(2rem,4vw,3.8rem); line-height:.98; }
    h2 { letter-spacing:-.025em; }
    code, pre, [data-testid="stMetricValue"] { font-family:'DM Mono', monospace; }
    .eyebrow { color:var(--teal); font:500 .72rem 'DM Mono',monospace; letter-spacing:.13em;
               text-transform:uppercase; margin-bottom:.55rem; }
    .lede { color:var(--muted); font-size:1.04rem; max-width:42rem; margin-top:-.7rem; }
    .topline { border-top:1px solid var(--line); margin:1.8rem 0 1.15rem; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:14px;
             padding:1.1rem 1.25rem; box-shadow:0 10px 24px rgba(23,35,43,.035); }
    .panel-label { color:var(--muted); font:500 .68rem 'DM Mono',monospace; letter-spacing:.12em;
                   text-transform:uppercase; margin-bottom:.55rem; }
    .decision { border-radius:16px; padding:1.35rem 1.5rem; border:1px solid var(--line);
                animation:rise .35s ease-out; }
    .decision.allow { background:var(--teal-soft); border-color:#a9dcd1; }
    .decision.deny { background:var(--coral-soft); border-color:#efb8ab; }
    .decision-word { font-size:2.1rem; font-weight:700; letter-spacing:-.04em; }
    .decision-rule { color:var(--muted); font:500 .78rem 'DM Mono',monospace; margin-top:.4rem; }
    .rule { padding:.78rem .85rem; border:1px solid var(--line); border-radius:10px; background:#fff; }
    .rule-name { font:500 .7rem 'DM Mono',monospace; color:var(--muted); }
    .rule-state { margin-top:.3rem; font-weight:600; }
    .pass { color:var(--teal); } .fail { color:var(--coral); }
    .trace-number { font:500 2.4rem 'DM Mono',monospace; line-height:1; }
    .trace-note { color:var(--muted); margin-top:.45rem; }
    .receipt { background:#172a2d; color:#dff3ee; border-radius:12px; padding:1rem 1.1rem;
               font:400 .76rem 'DM Mono',monospace; overflow-wrap:anywhere; }
    @keyframes rise { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)

policy = load_policy(PACKAGE_DIR / "policy.json")

with st.sidebar:
    st.markdown("<div class='eyebrow' style='color:#74d4c7'>PHAROS / LOCAL LAB</div>", unsafe_allow_html=True)
    st.markdown("## Policy gatekeeper")
    st.caption("A reviewer console for one question: does this action reach the executor?")
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown("**SCENARIO**")
    scenario_name = st.radio(
        "Choose a preset or build a request",
        [*SCENARIOS, "Custom request"],
        label_visibility="collapsed",
    )
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.caption("Trusted clock is fixed per preset. Every run uses a temporary audit file and a mock executor.")
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("`LOCAL SIMULATION`\n\nNo wallet · no RPC · no broadcast", unsafe_allow_html=False)

if scenario_name == "Custom request":
    st.sidebar.markdown("**CUSTOM REQUEST**")
    with st.sidebar.form("custom_request_form"):
        custom_id = st.text_input("Request ID", value="reviewer-custom-001")
        custom_amount = st.text_input("Amount", value="10.00", help="Keep this as text to test malformed input, such as 1.2.3.")
        custom_address = st.text_input("Destination address", value=ADDRESS)
        custom_contract = st.text_input("Contract address", value=CONTRACT)
        custom_time = st.time_input("Trusted demo clock", value=time(10, 0), step=60)
        submitted = st.form_submit_button("Evaluate request", type="primary")
    if submitted or "custom_result" not in st.session_state:
        st.session_state.custom_result = run_request(
            PACKAGE_DIR,
            {
                "request_id": custom_id,
                "amount": custom_amount,
                "address": custom_address,
                "contract": custom_contract,
            },
            datetime(2026, 11, 1, custom_time.hour, custom_time.minute, tzinfo=timezone.utc),
        )
    result = st.session_state.custom_result
else:
    scenario_changed = st.session_state.get("scenario_name") != scenario_name
    if scenario_changed or "result" not in st.session_state:
        st.session_state.result = run_scenario(PACKAGE_DIR, scenario_name)
        st.session_state.scenario_name = scenario_name
    result = st.session_state.result

st.markdown("<div class='eyebrow'>PHAROS POLICY GATEKEEPER / REVIEW CONSOLE</div>", unsafe_allow_html=True)
st.title("One request. Four checks.\nOne hard stop.")
st.markdown(
    "<p class='lede'>A local, deterministic view of the enforcement boundary. The existing "
    "<code>PolicyGatekeeper</code> evaluates the request; this screen only renders its result.</p>",
    unsafe_allow_html=True,
)
st.markdown("<div class='topline'></div>", unsafe_allow_html=True)

decision_class = result.decision.outcome
decision_word = result.decision.outcome.upper()
with st.container():
    st.markdown(
        f"<div class='decision {decision_class}'><div class='panel-label'>DECISION / {result.decision.request_id}</div>"
        f"<div class='decision-word'>{decision_word}</div>"
        f"<div class='decision-rule'>deciding rule · {result.decision.deciding_rule}</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:.9rem'></div>", unsafe_allow_html=True)
request_col, reason_col = st.columns([1.1, 1], gap="large")
with request_col:
    st.markdown("<div class='panel-label'>REQUEST PAYLOAD</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='panel'><div><strong>Amount</strong><br><code>{result.request['amount']}</code></div>"
        f"<div style='margin-top:.8rem'><strong>Destination</strong><br><code>{result.request['address']}</code></div>"
        f"<div style='margin-top:.8rem'><strong>Contract</strong><br><code>{result.request['contract']}</code></div></div>",
        unsafe_allow_html=True,
    )
with reason_col:
    st.markdown("<div class='panel-label'>WHY THIS DECISION</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='panel'><strong>{result.decision.reason}</strong>", unsafe_allow_html=True)
    if result.decision.violations:
        for violation in result.decision.violations:
            st.markdown(f"<div style='margin-top:.55rem;color:#df5c48'>• {violation}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-top:.55rem;color:#087f76'>• No policy violations found.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
st.markdown("<div class='panel-label'>RULE EVALUATION</div>", unsafe_allow_html=True)
rule_columns = st.columns(len(RULES))
for column, (rule, passed) in zip(rule_columns, rule_statuses(result.decision).items()):
    state_class = "pass" if passed else "fail"
    state = "PASS" if passed else "FAIL"
    column.markdown(
        f"<div class='rule'><div class='rule-name'>{rule}</div><div class='rule-state {state_class}'>● {state}</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
trace_col, policy_col = st.columns([1, 1.35], gap="large")
with trace_col:
    st.markdown("<div class='panel-label'>EXECUTION TRACE</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='panel'><div class='trace-number'>{result.executor_calls}</div>"
        "<div class='trace-note'>mock executor calls</div>"
        f"<div style='margin-top:1rem;color:{'#087f76' if result.executor_calls else '#df5c48'}'>"
        f"{'Allowed request reached the local mock.' if result.executor_calls else 'Denied request stopped before execution.'}</div></div>",
        unsafe_allow_html=True,
    )
with policy_col:
    st.markdown("<div class='panel-label'>ACTIVE POLICY</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='receipt'>{json.dumps(policy, indent=2)}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
st.markdown("<div class='panel-label'>AUDIT RECEIPT / TEMPORARY JSONL</div>", unsafe_allow_html=True)
st.dataframe(result.audit_entries, use_container_width=True, hide_index=True)
st.caption("Local simulation only. No transaction, wallet, RPC, or Pharos Skill Engine runtime was invoked.")