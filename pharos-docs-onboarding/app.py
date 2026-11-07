from __future__ import annotations

from datetime import datetime

import streamlit as st

from docs_agent.answer_engine import ground
from docs_agent.client import DocsMcpClient
from docs_agent.retrieval import retrieve


st.set_page_config(page_title="PHAROS DOCS EXPLORER", page_icon="✦", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --ink:#e7f1ed; --muted:#91a69f; --line:#29423b; --panel:#10231f; --mint:#b9f4d4; }
html, body, [class*="css"] { font-family:'Space Grotesk', sans-serif; }
code, .mono { font-family:'DM Mono', monospace; }
.hero { border-bottom:1px solid var(--line); padding:1.2rem 0 1rem; margin-bottom:1.2rem; }
.title { color:var(--ink); font-size:2rem; font-weight:700; letter-spacing:0; }
.sub { color:var(--muted); margin-top:.25rem; }
.pill { color:#10231f; background:var(--mint); border-radius:999px; padding:.35rem .7rem; font:500 .75rem 'DM Mono'; display:inline-block; }
.metric { border-top:2px solid var(--mint); padding-top:.55rem; }
.metric-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:var(--ink); font:500 1.15rem 'DM Mono'; margin-top:.2rem; }
.citation { border-left:3px solid var(--mint); padding:.45rem .7rem; margin:.4rem 0; background:var(--panel); }
</style>
""", unsafe_allow_html=True)


def get_client() -> DocsMcpClient:
    if "docs_client" not in st.session_state:
        st.session_state.docs_client = DocsMcpClient()
        st.session_state.history = []
    return st.session_state.docs_client


docs = get_client()
st.markdown('<div class="hero"><div class="title">PHAROS DOCS EXPLORER</div><div class="sub">Developer onboarding console · grounded answers from the official Docs query interface</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<span class="pill">● DOCS MCP / PUBLIC</span>', unsafe_allow_html=True)
    st.header("Connection")
    if st.button("Check connection", width="stretch"):
        st.session_state.connection = docs.check_connection()
    connection = st.session_state.get("connection", {"status": "Not checked", "endpoint": docs.index_url})
    st.metric("Status", connection["status"])
    st.caption(f"Query endpoint: {docs.base_url}")
    st.divider()
    st.caption("No credentials are required. The endpoint returns documentation answers and source references; it does not sign or broadcast transactions.")

metrics = st.columns(4)
for column, label, value in zip(metrics, ["MCP status", "Documentation source", "Successful queries", "Last retrieval"], [docs.last_status, "Official Pharos Docs", str(len(st.session_state.history)), st.session_state.history[-1]["time"] if st.session_state.history else "—"]):
    with column:
        st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)

if st.button("Check connection", type="secondary"):
    st.session_state.connection = docs.check_connection()
    st.rerun()

search_tab, history_tab, diagnostics_tab = st.tabs(["Ask the docs", "Query history", "MCP diagnostics"])
with search_tab:
    question = st.text_input("Documentation question", placeholder="How do I configure a Pharos MCP client?")
    goal = st.text_input("Developer goal", value="onboard a developer safely on Pharos")
    if st.button("Search documentation", type="primary"):
        with st.spinner("Querying official Pharos documentation..."):
            result = retrieve(docs, question, goal)
        if result.error:
            st.error(result.error)
        else:
            grounded = ground(result.response)
            st.session_state.history.insert(0, {"question": question, "answer": grounded, "time": datetime.now().strftime("%H:%M:%S")})
            st.rerun()
    if st.session_state.history:
        item = st.session_state.history[0]
        st.subheader(item["question"])
        answer = item["answer"]
        st.markdown(answer.answer)
        st.info(answer.interpretation)
        with st.expander("Retrieved excerpts", expanded=True):
            for fact in answer.facts:
                st.markdown(f"- {fact}")
        with st.expander(f"Citations ({len(answer.citations)})", expanded=True):
            if answer.citations:
                for citation in answer.citations:
                    st.markdown(f'<div class="citation"><a href="{citation["url"]}" target="_blank">{citation["title"]}</a></div>', unsafe_allow_html=True)
            else:
                st.warning("No source references were returned; treat this answer as insufficient evidence.")

with history_tab:
    if not st.session_state.history:
        st.info("No questions yet.")
    for item in st.session_state.history:
        with st.expander(f'{item["time"]} · {item["question"]}'):
            st.write(item["answer"].answer)
            st.caption(f'{len(item["answer"].citations)} citation(s) preserved')

with diagnostics_tab:
    st.write({"docs_endpoint": docs.base_url, "index_endpoint": docs.index_url, "status": docs.last_status, "requests": docs.request_count, "last_error": docs.last_error})
    st.caption("Verified official endpoints: Docs query interface and its llms.txt index. Chain MCP is a separate service documented at https://mcp.pharos.xyz/mcp.")