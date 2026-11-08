from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docs_search.client import DocsClient
from docs_search.retrieval import retrieve

st.set_page_config(page_title="PHAROS DOCS SEARCH", page_icon="⌘", layout="wide")
st.markdown("""<style>
body { background: #101417; }
.hero { border-bottom: 1px solid #354047; padding: 1rem 0 1.5rem; margin-bottom: 1.2rem; }
.hero h1 { color: #e9f1ec; letter-spacing: .04em; font-size: 2rem; }
.hero p { color: #9db0aa; }
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>PHAROS DOCS SEARCH</h1><p>Interactive Explorer · official Developer Docs query interface</p></div>', unsafe_allow_html=True)

if "client" not in st.session_state:
    st.session_state.client = DocsClient()
if "history" not in st.session_state:
    st.session_state.history = []
client: DocsClient = st.session_state.client

with st.sidebar:
    st.subheader("MCP diagnostics")
    if st.button("Check connection"):
        st.session_state.connection = client.check_connection()
    connection = st.session_state.get("connection", {"status": "Not checked", "endpoint": client.base_url})
    st.write(f"Status: **{connection['status']}**")
    st.caption(f"Docs query: {client.base_url}")
    st.caption("The search endpoint is documented as an HTTP ask interface. Chain MCP is a separate service.")
    st.subheader("Examples")
    for example in ["What is the Pharos mainnet chain ID?", "How do I deploy a contract with Foundry?", "How do I read ERC20 balances?"]:
        st.caption(example)

query = st.text_input("Documentation question", placeholder="Ask a specific Pharos development question")
if st.button("Search documentation", type="primary", disabled=not query.strip()):
    with st.spinner("Querying official documentation..."):
        result = retrieve(client, query)
    st.session_state.history.insert(0, result)

if st.session_state.history:
    result = st.session_state.history[0]
    if result.status == "error":
        st.error(result.error)
    else:
        st.caption(f"Status: {result.status} · Query: {result.query}")
        if result.answer:
            st.subheader("Retrieved answer")
            st.write(result.answer)
        if result.excerpts:
            st.subheader("Relevant excerpts")
            for excerpt in result.excerpts:
                st.info(excerpt)
        st.subheader("Sources")
        if result.sources:
            for source in result.sources:
                st.markdown(f"- [{source.title}]({source.url})")
        else:
            st.warning("No source references were returned; treat this result as insufficiently attributed.")
else:
    st.info("Enter a question to retrieve documentation from the live service.")

with st.expander(f"Search history ({len(st.session_state.history)})"):
    for item in st.session_state.history:
        st.write(f"{item.status}: {item.query}")
