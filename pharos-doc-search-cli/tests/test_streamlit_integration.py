from pathlib import Path


def test_streamlit_app_exists_and_uses_live_retrieval():
    app = Path(__file__).parents[1] / "streamlit_app" / "app.py"
    text = app.read_text(encoding="utf-8")
    assert "st.text_input" in text
    assert "retrieve(client, query)" in text
    assert "st.session_state.history" in text
