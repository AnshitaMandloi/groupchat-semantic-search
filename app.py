import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "search"))

import json
import streamlit as st
from datetime import datetime
from engine import SearchEngine

st.set_page_config(page_title="ChatMind — Group Chat Search", page_icon="💬", layout="wide")

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "data", "corpus.json")
QUERIES_PATH = os.path.join(os.path.dirname(__file__), "data", "queries.json")
EVAL_PATH = os.path.join(os.path.dirname(__file__), "data", "eval_results.json")

PARTICIPANT_COLORS = {
    "Priya": "#f472b6", "Rohan": "#60a5fa", "Aman": "#34d399", "Sneha": "#fbbf24",
    "Vikram": "#a78bfa", "Neha": "#fb923c", "Karan": "#22d3ee", "Ishaan": "#f87171",
}

CSS = """
<style>
.stApp { background-color: #0e1117; }
.chat-bubble {
    background: #1a1d24; border-radius: 14px; padding: 10px 16px; margin: 6px 0;
    max-width: 80%; border: 1px solid #262a33;
}
.chat-bubble.highlight {
    background: linear-gradient(135deg, #2d1b3d, #1a1d24);
    border: 1.5px solid #a78bfa; box-shadow: 0 0 18px rgba(167,139,250,0.35);
}
.sender-name { font-weight: 700; font-size: 0.82rem; margin-bottom: 2px; }
.msg-text { font-size: 0.98rem; color: #e5e7eb; }
.msg-time { font-size: 0.70rem; color: #6b7280; margin-top: 3px; }
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 600; margin-right: 6px;
}
.badge-semantic { background: #1e3a5f; color: #7dd3fc; }
.badge-attributed { background: #3f2d1e; color: #fdba74; }
.badge-temporal { background: #1e3f2d; color: #86efac; }
.score-pill {
    background: #262a33; color: #a78bfa; padding: 2px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 600;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def load_engine():
    return SearchEngine(CORPUS_PATH)


def fmt_time(iso_ts):
    dt = datetime.fromisoformat(iso_ts)
    return dt.strftime("%d %b %Y, %I:%M %p")


def render_bubble(msg, highlighted=False):
    color = PARTICIPANT_COLORS.get(msg["sender"], "#9ca3af")
    cls = "chat-bubble highlight" if highlighted else "chat-bubble"
    st.markdown(f"""
        <div class="{cls}">
            <div class="sender-name" style="color:{color}">{msg['sender']}</div>
            <div class="msg-text">{msg['text']}</div>
            <div class="msg-time">{fmt_time(msg['timestamp'])}</div>
        </div>
    """, unsafe_allow_html=True)


def render_result(result, rank):
    m = result["message"]
    ctx = result["context"]
    with st.container(border=True):
        top = st.columns([3, 1, 1])
        with top[0]:
            st.markdown(f"**Result #{rank}**")
        with top[1]:
            st.markdown(f'<span class="score-pill">relevance {result["score"]:.2f}</span>',
                        unsafe_allow_html=True)
        with top[2]:
            label = "Full thread" if ctx["type"] == "thread" else "Context window"
            st.caption(label)

        for cm in ctx["messages"]:
            render_bubble(cm, highlighted=(cm["id"] == m["id"]))


def search_tab(engine):
    st.markdown("### 🔍 Search the chat")
    st.caption("Ask it the way you'd ask a friend — meaning matters more than exact words.")

    example_cols = st.columns(4)
    examples = [
        "when did we decide on Manali",
        "what did Priya say about the budget",
        "what did we discuss last month",
        "which trek did we finally pick",
    ]
    for i, ex in enumerate(examples):
        if example_cols[i].button(ex, use_container_width=True):
            st.session_state["query_input"] = ex

    query = st.text_input("Search query", key="query_input",
                           placeholder="e.g. when did we finalize the trip destination?",
                           label_visibility="collapsed")
    top_k = st.slider("Number of results", 1, 10, 5)

    if query:
        with st.spinner("Searching..."):
            out = engine.search(query, top_k=top_k)

        badge_class = f"badge-{out['detected_type']}"
        badge_html = f'<span class="badge {badge_class}">{out["detected_type"].upper()}</span>'
        extra = ""
        if out["detected_sender"]:
            extra += f'<span class="badge" style="background:#262a33;color:#e5e7eb">from {out["detected_sender"]}</span>'
        if out["detected_date_range"]:
            d0 = datetime.fromisoformat(out["detected_date_range"][0]).strftime("%d %b")
            d1 = datetime.fromisoformat(out["detected_date_range"][1]).strftime("%d %b")
            extra += f'<span class="badge" style="background:#262a33;color:#e5e7eb">{d0} – {d1}</span>'
        st.markdown(badge_html + extra, unsafe_allow_html=True)

        if out["embed_mode"] == "none":
            st.warning(
                "Running in **BM25-only mode** — the semantic embedding model isn't loaded "
                "(needs internet to download on first run). Keyword-only matches will miss "
                "paraphrased queries. See README to enable full semantic mode.",
                icon="⚠️",
            )

        st.markdown("---")
        if not out["results"]:
            st.info("No results found.")
        for i, r in enumerate(out["results"], 1):
            render_result(r, i)


def eval_tab():
    st.markdown("### 📊 Evaluation Dashboard")
    st.caption("Benchmark against 41 ground-truth queries, run via `search/evaluate.py`.")

    if not os.path.exists(EVAL_PATH):
        st.info("No eval results yet. Run `python search/evaluate.py` first, then reload this page.")
        return

    with open(EVAL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    rows = data["rows"]
    embed_mode = data["embed_mode"]

    st.markdown(f"**Embedding mode:** `{embed_mode}`" +
                (" — full semantic search active ✅" if embed_mode != "none"
                 else " — BM25 fallback (no internet to fetch embedding model) ⚠️"))

    def pct(vals):
        return 100.0 * sum(vals) / len(vals) if vals else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total queries", len(rows))
    c2.metric("Top-1 accuracy", f"{pct([r['top1_hit'] for r in rows]):.0f}%")
    c3.metric("Top-5 accuracy", f"{pct([r['top5_hit'] for r in rows]):.0f}%")
    c4.metric("Context-hit rate", f"{pct([r['context_hit'] for r in rows]):.0f}%")

    st.markdown("#### By query type")
    for qtype in ["semantic", "attributed", "temporal"]:
        sub = [r for r in rows if r["query_type"] == qtype]
        if not sub:
            continue
        cols = st.columns([1, 1, 1, 1])
        cols[0].markdown(f"**{qtype.capitalize()}** (n={len(sub)})")
        cols[1].markdown(f"Top-1: {pct([r['top1_hit'] for r in sub]):.0f}%")
        cols[2].markdown(f"Top-5: {pct([r['top5_hit'] for r in sub]):.0f}%")
        cols[3].markdown(f"Context: {pct([r['context_hit'] for r in sub]):.0f}%")

    no_overlap = [r for r in rows if r["no_word_overlap"]]
    st.markdown("#### 🎯 No-word-overlap subset (the actual point of this project)")
    cols = st.columns(3)
    cols[0].metric("n", len(no_overlap))
    cols[1].metric("Top-1", f"{pct([r['top1_hit'] for r in no_overlap]):.0f}%")
    cols[2].metric("Context-hit", f"{pct([r['context_hit'] for r in no_overlap]):.0f}%")

    st.markdown("#### Full results")
    for r in rows:
        icon = "✅" if r["top5_hit"] else ("🟡" if r["context_hit"] else "❌")
        overlap_tag = " · no-overlap" if r["no_word_overlap"] else ""
        with st.expander(f"{icon} [{r['query_type']}{overlap_tag}] {r['query']}"):
            st.write(f"**Detected type:** {r['detected_type']}")
            st.write(f"**Top result:** {r['top1_result_text']}")
            st.write(f"**Top-1 hit:** {r['top1_hit']} · **Top-5 hit:** {r['top5_hit']} · "
                     f"**Context hit:** {r['context_hit']}")


def main():
    st.title("💬 ChatMind")
    st.caption("Semantic search over your group chat — understands meaning, not just words.")

    engine = load_engine()

    tab1, tab2 = st.tabs(["🔍 Search", "📊 Eval Dashboard"])
    with tab1:
        search_tab(engine)
    with tab2:
        eval_tab()


if __name__ == "__main__":
    main()
