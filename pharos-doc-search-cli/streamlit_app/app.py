from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docs_search.client import DocsClient
from docs_search.retrieval import retrieve

st.set_page_config(page_title="PHAROS DOCS SEARCH", page_icon=">_", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root { color-scheme: dark; }
html, body, [data-testid="stAppViewContainer"] { background: #0b0e0d; }
[data-testid="stHeader"] { background: #0b0e0d; }
* { font-family: 'IBM Plex Mono', 'Courier New', monospace !important; }
[data-testid="stSidebar"] { background: #0f1412; border-right: 1px solid #26342d; }
[data-testid="stSidebar"] section { padding-top: 1.2rem; }
.terminal-header { border: 1px solid #2b4939; background: #101813; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 0 28px rgba(80, 220, 130, .05); }
.terminal-title { color: #9dffb8; font-size: 1.35rem; font-weight: 600; letter-spacing: .06em; }
.terminal-subtitle { color: #718b79; font-size: .75rem; margin-top: .45rem; }
.prompt { color: #9dffb8; margin-right: .55rem; }
.command-line { color: #d3e6d8; background: #0a0d0b; border-left: 2px solid #54d47a; padding: .65rem .8rem; margin: .8rem 0 1rem; }
.panel { border: 1px solid #263b30; background: #0f1511; padding: .85rem 1rem; margin: .75rem 0; }
.panel-label { color: #7b9d85; font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; margin-bottom: .55rem; }
.status-ok { color: #9dffb8; }
.status-warn { color: #f0c674; }
.status-error { color: #ff7b72; }
.source-line { border-top: 1px solid #1f3026; padding: .55rem 0; }
.source-line a { color: #8bd5ff; }
div[data-testid="stTextInput"] input { background: #080b09; color: #d3e6d8; border: 1px solid #385643; border-radius: 0; }
div[data-testid="stTextInput"] input:focus { border-color: #9dffb8; box-shadow: 0 0 0 1px #9dffb8; }
div.stButton > button { border: 1px solid #3c6b4b; border-radius: 0; background: #14251a; color: #a9ffbf; }
div.stButton > button:hover { border-color: #9dffb8; color: #ffffff; }
div[data-testid="stAlert"] { border-radius: 0; background: #101813; }
div[data-testid="stExpander"] { border: 1px solid #263b30; border-radius: 0; background: #0f1511; }
code { color: #9dffb8; }
</style>""", unsafe_allow_html=True)
st.markdown("""<div class="terminal-header">
<div class="terminal-title"><span class="prompt">pharos@docs:~$</span> PHAROS DOCS SEARCH</div>
<div class="terminal-subtitle">interactive documentation console // live Developer Docs query interface</div>
</div>""", unsafe_allow_html=True)

if "client" not in st.session_state:
    st.session_state.client = DocsClient()
if "history" not in st.session_state:
    st.session_state.history = []
client: DocsClient = st.session_state.client

with st.sidebar:
    st.markdown('<div class="panel-label">[ diagnostics ]</div>', unsafe_allow_html=True)
    if st.button("Check connection"):
        st.session_state.connection = client.check_connection()
    connection = st.session_state.get("connection", {"status": "Not checked", "endpoint": client.base_url})
    status_class = "status-ok" if connection["status"] == "Connected" else "status-warn"
    st.markdown(f'<div class="panel"><div class="panel-label">connection</div><span class="{status_class}">● {connection["status"]}</span><br><span style="color:#718b79;font-size:.7rem;">{client.base_url}</span></div>', unsafe_allow_html=True)
    st.caption("Docs search uses the documented HTTP ask interface. Chain MCP is separate.")
    st.markdown('<div class="panel-label">[ example queries ]</div>', unsafe_allow_html=True)
    for example in ["What is the Pharos mainnet chain ID?", "How do I deploy a contract with Foundry?", "How do I read ERC20 balances?"]:
        st.markdown(f'<div style="color:#9db7a3;font-size:.7rem;margin:.5rem 0;">$ {example}</div>', unsafe_allow_html=True)

st.markdown('<div class="command-line"><span class="prompt">pharos@docs:~$</span> search --query</div>', unsafe_allow_html=True)
query = st.text_input("Documentation question", placeholder="type a natural-language question", label_visibility="collapsed")
if st.button("Search documentation", type="primary", disabled=not query.strip()):
    with st.spinner("Querying official documentation..."):
        result = retrieve(client, query)
    st.session_state.history.insert(0, result)

if st.session_state.history:
    result = st.session_state.history[0]
    if result.status == "error":
        st.markdown(f'<div class="panel"><span class="status-error">[ error ] {result.error}</span></div>', unsafe_allow_html=True)
    else:
        result_class = "status-ok" if result.status == "success" else "status-warn"
        st.markdown(f'<div class="panel"><div class="panel-label">last command</div><span class="prompt">$</span> {result.query}<br><span class="{result_class}">[ {result.status} ]</span></div>', unsafe_allow_html=True)
        if result.answer:
            st.markdown('<div class="panel-label">[ retrieved answer ]</div>', unsafe_allow_html=True)
            st.code(result.answer, language="text")
        if result.excerpts:
            st.markdown('<div class="panel-label">[ relevant excerpts ]</div>', unsafe_allow_html=True)
            for excerpt in result.excerpts:
                st.code(excerpt, language="text")
        st.markdown('<div class="panel-label">[ sources ]</div>', unsafe_allow_html=True)
        if result.sources:
            for source in result.sources:
                st.markdown(f'<div class="source-line">↳ <a href="{source.url}" target="_blank">{source.title}</a><br><span style="color:#718b79;font-size:.7rem;">{source.url}</span></div>', unsafe_allow_html=True)
        else:
            st.warning("No source references were returned; treat this result as insufficiently attributed.")
else:
    st.markdown('<div class="panel"><span class="status-warn">[ idle ]</span> Enter a question to retrieve live documentation.</div>', unsafe_allow_html=True)

with st.expander(f"Search history ({len(st.session_state.history)})"):
    for item in st.session_state.history:
        st.write(f"{item.status}: {item.query}")
