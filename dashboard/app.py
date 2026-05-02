"""
Rapid Remedy — Doctor's Dashboard v3
ChatGPT-style layout: saved sessions in sidebar, A/B comparison in main panel
Modes: Single Query | Naive vs Optimized | HyDE + MMR
"""

import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Rapid Remedy",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #0c0e14;
        color: #d4d8e2;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #080a10;
        border-right: 1px solid #1a1f2e;
        width: 280px !important;
    }

    [data-testid="stSidebar"] .stMarkdown p {
        color: #6b7280;
        font-size: 12px;
    }

    /* ── Chat history items ── */
    .chat-item {
        background: #111520;
        border: 1px solid #1a1f2e;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 6px;
        cursor: pointer;
        transition: border-color 0.15s;
    }

    .chat-item:hover {
        border-color: #2563eb;
    }

    .chat-item.active {
        border-color: #2563eb;
        background: #0f1829;
    }

    .chat-item .chat-title {
        font-size: 12px;
        font-weight: 500;
        color: #c9d1e0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 3px;
    }

    .chat-item .chat-meta {
        font-size: 10px;
        color: #3d4759;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* ── Pill badges ── */
    .pill {
        display: inline-block;
        border-radius: 20px;
        padding: 2px 9px;
        font-size: 10px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 500;
        letter-spacing: 0.04em;
        margin-right: 4px;
    }
    .pill-blue  { background: #0f2040; color: #60a5fa; border: 1px solid #1e3a6e; }
    .pill-green { background: #052510; color: #34d399; border: 1px solid #0a4020; }
    .pill-red   { background: #200a0a; color: #f87171; border: 1px solid #4a1010; }
    .pill-purple{ background: #160e2a; color: #a78bfa; border: 1px solid #2e1c5a; }
    .pill-yellow{ background: #1f1500; color: #fbbf24; border: 1px solid #4a3400; }

    /* ── Section labels ── */
    .section-label {
        font-size: 10px;
        font-weight: 600;
        color: #3d4759;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid #1a1f2e;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: #0f1218;
        border: 1px solid #1a1f2e;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
    }

    .metric-card .val {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 24px;
        font-weight: 600;
        line-height: 1.2;
    }

    .metric-card .lbl {
        font-size: 10px;
        color: #3d4759;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }

    .val-blue   { color: #60a5fa; }
    .val-green  { color: #34d399; }
    .val-red    { color: #f87171; }
    .val-purple { color: #a78bfa; }
    .val-yellow { color: #fbbf24; }

    /* ── Suggestion output ── */
    .suggestion-box {
        background: #0a0e18;
        border: 1px solid #1a1f2e;
        border-left: 3px solid #2563eb;
        border-radius: 0 10px 10px 0;
        padding: 18px 20px;
        font-size: 13.5px;
        line-height: 1.75;
        color: #c9d1e0;
    }

    .suggestion-box.naive {
        border-left-color: #f87171;
    }

    .suggestion-box.optimized {
        border-left-color: #34d399;
    }

    .suggestion-box.hyde {
        border-left-color: #a78bfa;
    }

    /* ── Pipeline headers ── */
    .pipeline-header {
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 14px;
    }

    .ph-naive     { background: #1a0808; border: 1px solid #4a1010; color: #f87171; }
    .ph-optimized { background: #081a08; border: 1px solid #104a10; color: #34d399; }
    .ph-hyde      { background: #12081a; border: 1px solid #2e1c5a; color: #a78bfa; }

    /* ── HyDE hypothesis box ── */
    .hyde-box {
        background: #12081a;
        border: 1px solid #2e1c5a;
        border-radius: 8px;
        padding: 14px;
        font-size: 12px;
        color: #c4b5fd;
        font-style: italic;
        line-height: 1.6;
        margin-bottom: 14px;
    }

    .hyde-box .hyde-label {
        font-size: 10px;
        font-weight: 600;
        color: #a78bfa;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
        font-style: normal;
    }

    /* ── Warning banner ── */
    .warn {
        background: #1a1000;
        border: 1px solid #4a3000;
        border-radius: 8px;
        padding: 9px 14px;
        color: #fbbf24;
        font-size: 12px;
        margin-bottom: 18px;
    }

    /* ── Hero ── */
    .hero-wrap {
        padding: 32px 0 20px;
        text-align: center;
    }

    .hero-title {
        font-size: 38px;
        font-weight: 600;
        letter-spacing: -0.02em;
        background: linear-gradient(120deg, #60a5fa 0%, #a78bfa 60%, #34d399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }

    .hero-sub {
        color: #3d4759;
        font-size: 13px;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* ── Input area ── */
    .stTextArea textarea, .stTextInput input {
        background: #0f1218 !important;
        border: 1px solid #1a1f2e !important;
        color: #d4d8e2 !important;
        border-radius: 8px !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 14px !important;
    }

    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37,99,235,0.15) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: #1d4ed8 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        letter-spacing: 0.02em !important;
        transition: background 0.15s !important;
    }

    .stButton > button:hover {
        background: #2563eb !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background: #0f1218;
        border: 1px solid #1a1f2e;
        border-radius: 6px;
        color: #6b7280;
        font-size: 12px;
        padding: 6px 14px;
    }

    .stTabs [aria-selected="true"] {
        background: #0f2040 !important;
        color: #60a5fa !important;
        border-color: #1e3a6e !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: #0f1218 !important;
        border: 1px solid #1a1f2e !important;
        border-radius: 7px !important;
        color: #6b7280 !important;
        font-size: 12px !important;
    }

    /* ── Divider ── */
    hr { border-color: #1a1f2e !important; }

    /* ── Mode selector radio ── */
    .stRadio > div {
        gap: 6px;
    }

    /* ── Slider ── */
    .stSlider [data-baseweb="slider"] {
        margin-top: 6px;
    }

    /* ── Summary impact row ── */
    .impact-row {
        display: flex;
        gap: 14px;
        margin-top: 14px;
    }

    .impact-cell {
        flex: 1;
        background: #0a0e18;
        border: 1px solid #1a1f2e;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }

    .impact-cell .big {
        font-size: 30px;
        font-weight: 700;
        font-family: 'IBM Plex Mono', monospace;
    }

    .impact-cell .sub {
        font-size: 10px;
        color: #3d4759;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }

    .impact-cell .delta {
        font-size: 11px;
        color: #3d4759;
        margin-top: 2px;
        font-family: 'IBM Plex Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of session dicts
if "active_session" not in st.session_state:
    st.session_state.active_session = None


# ── API helpers ───────────────────────────────────────────────────────────────
def call_query(symptoms, patient_context, top_k,
               use_reranking=False, use_compression=False,
               use_hyde=False, use_mmr=False):
    try:
        r = requests.post(f"{API_BASE}/query", json={
            "symptoms": symptoms,
            "patient_context": patient_context,
            "top_k": top_k,
            "use_reranking": use_reranking,
            "use_compression": use_compression,
            "use_hyde": use_hyde,
            "use_mmr": use_mmr,
        }, timeout=90)
        if r.status_code == 200:
            return r.json(), None
        return None, f"API error {r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)


def call_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def call_stats():
    try:
        r = requests.get(f"{API_BASE}/stats", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


# ── Render helpers ────────────────────────────────────────────────────────────
def render_metrics(data, color_class="blue"):
    opt = data.get("optimization", {})
    cols = st.columns(4)
    vals = [
        (f"{data.get('total_latency_ms',0):.0f}ms", "Total Latency", color_class),
        (str(data.get("tokens_used", 0)), "Tokens Used", "green"),
        (f"{opt.get('token_savings_pct',0)}%", "Token Savings", "yellow"),
        (str(opt.get("final_chunks", 0)), "Chunks Used", "purple"),
    ]
    for col, (val, lbl, cls) in zip(cols, vals):
        col.markdown(f"""
        <div class="metric-card">
            <div class="val val-{cls}">{val}</div>
            <div class="lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)


def render_latency_breakdown(data):
    stages = {
        "Retrieval": data.get("retrieval_latency_ms", 0),
        "HyDE":      data.get("hyde_latency_ms", 0),
        "Reranking": data.get("rerank_latency_ms", 0),
        "MMR":       data.get("mmr_latency_ms", 0),
        "Compression": data.get("compression_latency_ms", 0),
        "LLM":       data.get("llm_latency_ms", 0),
    }
    # Filter out zero stages for cleaner chart
    stages = {k: v for k, v in stages.items() if v > 0}
    colors = {
        "Retrieval": "#60a5fa",
        "HyDE": "#a78bfa",
        "Reranking": "#818cf8",
        "MMR": "#c084fc",
        "Compression": "#34d399",
        "LLM": "#fbbf24",
    }
    fig = go.Figure(go.Bar(
        x=list(stages.values()),
        y=list(stages.keys()),
        orientation='h',
        marker_color=[colors.get(k, "#60a5fa") for k in stages],
        text=[f"{v:.1f}ms" for v in stages.values()],
        textposition='outside',
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#6b7280', size=11, family='IBM Plex Mono'),
        margin=dict(l=10, r=80, t=10, b=10),
        height=max(140, len(stages) * 35),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_suggestion(text, variant="default"):
    css_class = {
        "naive": "suggestion-box naive",
        "optimized": "suggestion-box optimized",
        "hyde": "suggestion-box hyde",
    }.get(variant, "suggestion-box")
    # Escape HTML in text
    safe_text = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    st.markdown(f'<div class="{css_class}">{safe_text}</div>', unsafe_allow_html=True)


def render_hyde_hypothesis(opt):
    hyp = opt.get("hyde_hypothesis", "")
    if hyp:
        safe = hyp.replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(f"""
        <div class="hyde-box">
            <div class="hyde-label">🔮 HyDE Hypothetical Document (used for retrieval)</div>
            {safe}
        </div>""", unsafe_allow_html=True)


def render_chunks(chunks):
    for i, chunk in enumerate(chunks):
        score = chunk.get("rerank_score", 0)
        badge = "🟢 High" if score >= 5 else ("🟡 Mid" if score >= 0 else "🔴 Low")
        compressed = chunk.get("compressed_text", "")
        original   = chunk.get("original_text", "")
        savings    = round((1 - len(compressed) / max(len(original), 1)) * 100)
        tokens     = chunk.get("tokens_used", 0)

        with st.expander(f"Ref {i+1} · Abstract {chunk.get('abstract_id','')} · {badge} · {tokens} tokens"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Sent to LLM**")
                st.markdown(f'<div style="background:#0a0e18;border:1px solid #1a1f2e;border-radius:8px;padding:12px;font-size:12px;color:#c9d1e0;line-height:1.7">{compressed}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f"**Original ({savings}% compressed)**")
                st.markdown(f'<div style="background:#0f1218;border:1px solid #1a1f2e;border-radius:8px;padding:12px;font-size:12px;color:#4b5563;line-height:1.7">{original}</div>', unsafe_allow_html=True)


def render_pipeline_result(data, variant="default", label=""):
    """Renders a full pipeline result card."""
    ph_class = {"naive": "ph-naive", "optimized": "ph-optimized", "hyde": "ph-hyde"}.get(variant, "ph-optimized")
    if label:
        st.markdown(f'<div class="pipeline-header {ph_class}">{label}</div>', unsafe_allow_html=True)

    render_metrics(data, color_class="blue")

    opt = data.get("optimization", {})

    tab1, tab2, tab3 = st.tabs(["💊 Suggestion", "⏱ Latency", "📄 Chunks"])
    with tab1:
        if variant == "hyde":
            render_hyde_hypothesis(opt)
        render_suggestion(data.get("suggestion", ""), variant)
    with tab2:
        render_latency_breakdown(data)
    with tab3:
        render_chunks(data.get("chunks", []))


def render_comparison_chart(results: dict):
    """Bar chart comparing multiple pipelines."""
    labels = list(results.keys())
    latencies = [r.get("total_latency_ms", 0) for r in results.values()]
    tokens    = [r.get("tokens_used", 0) for r in results.values()]
    savings   = [r.get("optimization", {}).get("token_savings_pct", 0) for r in results.values()]

    palette = ["#f87171", "#34d399", "#a78bfa", "#60a5fa"][:len(labels)]

    fig = go.Figure(data=[
        go.Bar(name="Total Latency (ms)", x=labels, y=latencies,
               marker_color=palette, opacity=0.8,
               yaxis="y", offsetgroup=0),
        go.Bar(name="Tokens Used", x=labels, y=tokens,
               marker_color=palette,
               yaxis="y2", offsetgroup=1),
    ])
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#6b7280', size=11, family='IBM Plex Mono'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#6b7280', size=10)),
        margin=dict(l=10, r=10, t=20, b=10),
        height=260,
        yaxis=dict(showgrid=True, gridcolor='#1a1f2e', title="Latency (ms)", title_font=dict(size=10)),
        yaxis2=dict(overlaying='y', side='right', title="Tokens", title_font=dict(size=10), showgrid=False),
        xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo / title
    st.markdown("""
    <div style="padding:16px 4px 8px">
        <div style="font-size:16px;font-weight:600;color:#d4d8e2;letter-spacing:-0.01em">🏥 Rapid Remedy</div>
        <div style="font-size:10px;color:#3d4759;font-family:'IBM Plex Mono',monospace;margin-top:2px">Clinical RAG · Vector Search Benchmark</div>
    </div>
    """, unsafe_allow_html=True)

    health = call_health()
    if health:
        count_str = health.get("db", "").split("(")[-1].replace(")", "").strip() if "(" in health.get("db","") else ""
        st.markdown(f"""
        <div style="background:#051a0a;border:1px solid #0a3a14;border-radius:7px;padding:8px 12px;margin-bottom:14px">
            <span style="color:#34d399;font-size:11px">● API Connected</span>
            <span style="color:#3d4759;font-size:10px;display:block;margin-top:2px;font-family:'IBM Plex Mono',monospace">{count_str}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#1a0505;border:1px solid #4a0a0a;border-radius:7px;padding:8px 12px;margin-bottom:14px">
            <span style="color:#f87171;font-size:11px">● API Offline</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Pipeline settings ──
    st.markdown('<div class="section-label">Pipeline Settings</div>', unsafe_allow_html=True)
    top_k           = st.slider("Top-K chunks", 1, 10, 5)
    use_reranking   = st.toggle("Cross-encoder reranking", value=True)
    use_compression = st.toggle("Context compression", value=True)
    use_hyde        = st.toggle("HyDE query expansion", value=False,
                                help="Generates a hypothetical clinical abstract from your symptoms, then embeds that for retrieval. Improves recall for short queries.")
    use_mmr         = st.toggle("MMR diversity filter", value=False,
                                help="Maximal Marginal Relevance: selects diverse chunks instead of near-duplicates. Gives LLM broader medical coverage.")

    st.markdown("---")

    # ── Mode ──
    st.markdown('<div class="section-label">Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "mode",
        ["Single Query", "Naive vs Optimized", "Full Pipeline Compare"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── Chat history ──
    st.markdown('<div class="section-label">Session History</div>', unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown('<div style="color:#2a3040;font-size:12px;padding:8px 4px">No queries yet</div>', unsafe_allow_html=True)
    else:
        for i, session in enumerate(reversed(st.session_state.chat_history)):
            idx = len(st.session_state.chat_history) - 1 - i
            is_active = st.session_state.active_session == idx
            active_class = "active" if is_active else ""
            symptoms_preview = session["symptoms"][:38] + "…" if len(session["symptoms"]) > 38 else session["symptoms"]
            mode_pill = session.get("mode_label", "query")

            if st.button(
                f"{'▶ ' if is_active else ''}{symptoms_preview}",
                key=f"hist_{idx}",
                use_container_width=True,
            ):
                st.session_state.active_session = idx
                st.rerun()

            st.markdown(f"""
            <div style="font-size:10px;color:#3d4759;font-family:'IBM Plex Mono',monospace;margin:-6px 0 6px 4px">
                {session.get('timestamp','')} · {mode_pill}
            </div>""", unsafe_allow_html=True)

    if st.session_state.chat_history:
        if st.button("🗑 Clear history", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.active_session = None
            st.rerun()

    st.markdown("---")

    # ── Dataset distribution ──
    stats = call_stats()
    if stats:
        st.markdown('<div class="section-label">Dataset</div>', unsafe_allow_html=True)
        dist = stats.get("label_distribution", [])
        if dist:
            df_dist = pd.DataFrame(dist)
            fig = px.bar(df_dist, x="count", y="label", orientation='h',
                         color_discrete_sequence=["#1d4ed8"])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#6b7280', size=9, family='IBM Plex Mono'),
                margin=dict(l=0, r=0, t=0, b=0), height=180,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, title=""),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">Rapid Remedy</div>
    <div class="hero-sub">medical rag · vector search benchmark · v3.0</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="warn">⚠ Research purposes only — always consult a licensed physician for medical decisions.</div>', unsafe_allow_html=True)

# ── If a history session is active, show it ───────────────────────────────────
if st.session_state.active_session is not None:
    idx = st.session_state.active_session
    if 0 <= idx < len(st.session_state.chat_history):
        session = st.session_state.chat_history[idx]
        st.markdown(f"""
        <div style="background:#0a0e18;border:1px solid #1a1f2e;border-radius:10px;padding:14px 18px;margin-bottom:18px">
            <div style="font-size:10px;color:#3d4759;font-family:'IBM Plex Mono',monospace;margin-bottom:6px">
                SAVED SESSION · {session.get('timestamp','')} · {session.get('mode_label','')}
            </div>
            <div style="font-size:14px;color:#d4d8e2;font-weight:500">{session['symptoms']}</div>
            {f'<div style="font-size:12px;color:#6b7280;margin-top:4px">{session["patient_context"]}</div>' if session.get("patient_context") else ""}
        </div>
        """, unsafe_allow_html=True)

        col_back, _ = st.columns([1, 5])
        with col_back:
            if st.button("← New Query"):
                st.session_state.active_session = None
                st.rerun()

        # Re-render stored results
        stored = session.get("results", {})
        if "single" in stored:
            st.markdown("---")
            render_pipeline_result(stored["single"], "optimized", "")
        elif "naive" in stored and "opt" in stored:
            st.markdown("---")
            st.markdown('<div class="section-label">Performance Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({"⚡ Naive": stored["naive"], "🚀 Optimized": stored["opt"]})
            c1, c2 = st.columns(2)
            with c1:
                render_pipeline_result(stored["naive"], "naive", "⚡ Naive RAG — No Optimization")
            with c2:
                render_pipeline_result(stored["opt"], "optimized", "🚀 Optimized RAG — Full Pipeline")
        elif "naive" in stored and "opt" in stored and "hyde" in stored:
            pass  # handled below
        st.stop()

# ── Input form ────────────────────────────────────────────────────────────────
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    symptoms = st.text_area(
        "Patient Symptoms",
        placeholder="e.g. chest pain, shortness of breath, diaphoresis, radiating left arm pain…",
        height=96,
    )
with col_in2:
    patient_context = st.text_area(
        "Patient Context (optional)",
        placeholder="e.g. 55yo male, smoker, hypertension, family history of CAD…",
        height=96,
    )

run = st.button("⬡  Run Clinical Query", use_container_width=True)

# ── Mode: Single Query ────────────────────────────────────────────────────────
if mode == "Single Query" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        active_flags = []
        if use_reranking:  active_flags.append("rerank")
        if use_compression: active_flags.append("compress")
        if use_hyde:       active_flags.append("HyDE")
        if use_mmr:        active_flags.append("MMR")

        with st.spinner("Running pipeline…"):
            data, err = call_query(symptoms, patient_context, top_k,
                                   use_reranking, use_compression, use_hyde, use_mmr)
        if err:
            st.error(f"Error: {err}")
        else:
            # Save to history
            st.session_state.chat_history.append({
                "symptoms": symptoms,
                "patient_context": patient_context,
                "timestamp": datetime.now().strftime("%H:%M"),
                "mode_label": "single · " + ("+".join(active_flags) if active_flags else "naive"),
                "results": {"single": data},
            })

            st.markdown("---")
            variant = "hyde" if use_hyde else "optimized"
            render_pipeline_result(data, variant, "")

# ── Mode: Naive vs Optimized ──────────────────────────────────────────────────
elif mode == "Naive vs Optimized" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        with st.spinner("Running both pipelines…"):
            naive_data, naive_err = call_query(symptoms, patient_context, top_k,
                                               use_reranking=False, use_compression=False,
                                               use_hyde=False, use_mmr=False)
            opt_data, opt_err = call_query(symptoms, patient_context, top_k,
                                           use_reranking=True, use_compression=True,
                                           use_hyde=False, use_mmr=False)

        if naive_err or opt_err:
            st.error(naive_err or opt_err)
        else:
            # Save
            st.session_state.chat_history.append({
                "symptoms": symptoms,
                "patient_context": patient_context,
                "timestamp": datetime.now().strftime("%H:%M"),
                "mode_label": "A/B compare",
                "results": {"naive": naive_data, "opt": opt_data},
            })

            st.markdown("---")
            st.markdown('<div class="section-label">Performance Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({"⚡ Naive": naive_data, "🚀 Optimized": opt_data})

            c1, c2 = st.columns(2)
            with c1:
                render_pipeline_result(naive_data, "naive", "⚡ Naive RAG — No Optimization")
            with c2:
                render_pipeline_result(opt_data, "optimized", "🚀 Optimized RAG — Full Pipeline")

            # Impact summary
            st.markdown("---")
            st.markdown('<div class="section-label">Optimization Impact Summary</div>', unsafe_allow_html=True)

            n_tok = naive_data.get("tokens_used", 1)
            o_tok = opt_data.get("tokens_used", 1)
            n_lat = naive_data.get("total_latency_ms", 1)
            o_lat = opt_data.get("total_latency_ms", 1)
            tok_delta = round((1 - o_tok / n_tok) * 100, 1)
            lat_delta = round((1 - o_lat / n_lat) * 100, 1)
            tok_saved = n_tok - o_tok

            col1, col2, col3 = st.columns(3)
            col1.markdown(f"""
            <div class="impact-cell">
                <div class="big val-green">{tok_delta}%</div>
                <div class="sub">Token Reduction</div>
                <div class="delta">↑ {tok_saved} tokens saved</div>
            </div>""", unsafe_allow_html=True)
            col2.markdown(f"""
            <div class="impact-cell">
                <div class="big {'val-green' if lat_delta > 0 else 'val-red'}">{lat_delta:+.1f}%</div>
                <div class="sub">Latency Change</div>
                <div class="delta">{abs(n_lat - o_lat):.0f}ms difference</div>
            </div>""", unsafe_allow_html=True)
            rerank_in  = opt_data.get("optimization", {}).get("candidates_retrieved", 0)
            rerank_out = opt_data.get("optimization", {}).get("final_chunks", 0)
            col3.markdown(f"""
            <div class="impact-cell">
                <div class="big val-purple">{rerank_in}→{rerank_out}</div>
                <div class="sub">Reranking Filter</div>
                <div class="delta">candidates → final chunks</div>
            </div>""", unsafe_allow_html=True)

# ── Mode: Full Pipeline Compare (Naive / Optimized / HyDE+MMR) ───────────────
elif mode == "Full Pipeline Compare" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        with st.spinner("Running all three pipelines…"):
            naive_data, naive_err = call_query(symptoms, patient_context, top_k,
                                               False, False, False, False)
            opt_data, opt_err = call_query(symptoms, patient_context, top_k,
                                           True, True, False, False)
            hyde_data, hyde_err = call_query(symptoms, patient_context, top_k,
                                             True, True, True, True)

        errors = [e for e in [naive_err, opt_err, hyde_err] if e]
        if errors:
            st.error(errors[0])
        else:
            st.session_state.chat_history.append({
                "symptoms": symptoms,
                "patient_context": patient_context,
                "timestamp": datetime.now().strftime("%H:%M"),
                "mode_label": "3-way compare",
                "results": {"naive": naive_data, "opt": opt_data, "hyde": hyde_data},
            })

            st.markdown("---")
            st.markdown('<div class="section-label">Three-Pipeline Performance Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({
                "⚡ Naive": naive_data,
                "🚀 Optimized": opt_data,
                "🔮 HyDE+MMR": hyde_data,
            })

            c1, c2, c3 = st.columns(3)
            with c1:
                render_pipeline_result(naive_data, "naive", "⚡ Naive RAG")
            with c2:
                render_pipeline_result(opt_data, "optimized", "🚀 Optimized RAG")
            with c3:
                render_pipeline_result(hyde_data, "hyde", "🔮 HyDE + MMR")

            # 3-way impact table
            st.markdown("---")
            st.markdown('<div class="section-label">Three-Way Benchmark Results</div>', unsafe_allow_html=True)

            pipelines = {
                "⚡ Naive": naive_data,
                "🚀 Optimized": opt_data,
                "🔮 HyDE+MMR": hyde_data,
            }
            rows = []
            for name, d in pipelines.items():
                opt = d.get("optimization", {})
                rows.append({
                    "Pipeline": name,
                    "Latency (ms)": round(d.get("total_latency_ms", 0)),
                    "Tokens": d.get("tokens_used", 0),
                    "Token Savings %": opt.get("token_savings_pct", 0),
                    "Chunks Used": opt.get("final_chunks", 0),
                    "Retrieval (ms)": round(d.get("retrieval_latency_ms", 0), 1),
                    "HyDE (ms)": round(d.get("hyde_latency_ms", 0), 1),
                    "Rerank (ms)": round(d.get("rerank_latency_ms", 0), 1),
                    "MMR (ms)": round(d.get("mmr_latency_ms", 0), 1),
                    "LLM (ms)": round(d.get("llm_latency_ms", 0), 1),
                })
            df_bench = pd.DataFrame(rows)
            st.dataframe(df_bench, use_container_width=True, hide_index=True)