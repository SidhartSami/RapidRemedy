"""
Rapid Remedy — Doctor's Dashboard v4
Black & white minimalist theme — ChatGPT-style layout
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
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — Black & White Minimalist ────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

    /* ── Reset & base ── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 14px;
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu        { visibility: hidden; }
    footer           { visibility: hidden; }
    header           { visibility: hidden; }
    .stDeployButton  { display: none; }

    /* ── App background ── */
    .stApp {
        background-color: #212121;
        color: #ececec;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #171717;
        border-right: 1px solid #2a2a2a;
        padding-top: 0 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
    }

    /* Sidebar text */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: #b0b0b0 !important;
        font-size: 13px;
    }

    /* ── Sidebar logo block ── */
    .sb-logo {
        padding: 20px 16px 14px;
        border-bottom: 1px solid #2a2a2a;
        margin-bottom: 6px;
    }

    .sb-logo-title {
        font-size: 15px;
        font-weight: 600;
        color: #ececec;
        letter-spacing: -0.01em;
    }

    .sb-logo-sub {
        font-size: 11px;
        color: #555;
        margin-top: 2px;
    }

    /* ── Section labels ── */
    .section-label {
        font-size: 11px;
        font-weight: 500;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 14px 0 8px;
        padding-bottom: 6px;
        border-bottom: 1px solid #2a2a2a;
    }

    /* ── Status badge ── */
    .status-badge {
        border-radius: 6px;
        padding: 7px 12px;
        font-size: 12px;
        margin-bottom: 10px;
    }

    .status-online {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        color: #ececec;
    }

    .status-offline {
        background: #1a1a1a;
        border: 1px solid #3a3a3a;
        color: #888;
    }

    .status-dot-on  { color: #ececec; }
    .status-dot-off { color: #555;    }

    /* ── History items ── */
    .stButton > button {
        background: transparent !important;
        color: #b0b0b0 !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 8px 10px !important;
        transition: background 0.12s, border-color 0.12s !important;
    }

    .stButton > button:hover {
        background: #2a2a2a !important;
        border-color: #3a3a3a !important;
        color: #ececec !important;
    }

    /* Run button — primary ── */
    div[data-testid="stButton"]:has(button[kind="primary"]) > button,
    .run-btn > button {
        background: #ececec !important;
        color: #212121 !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 0 !important;
    }

    div[data-testid="stButton"]:has(button[kind="primary"]) > button:hover,
    .run-btn > button:hover {
        background: #ffffff !important;
    }

    /* ── Main content container ── */
    .main .block-container {
        max-width: 860px;
        margin: 0 auto;
        padding: 32px 24px 80px;
    }

    /* ── Hero ── */
    .hero {
        text-align: center;
        padding: 48px 0 32px;
    }

    .hero-title {
        font-size: 32px;
        font-weight: 600;
        color: #ececec;
        letter-spacing: -0.025em;
        margin-bottom: 6px;
    }

    .hero-sub {
        font-size: 13px;
        color: #555;
    }

    /* ── Warning banner ── */
    .warn-bar {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        padding: 9px 14px;
        font-size: 12px;
        color: #888;
        margin-bottom: 24px;
        text-align: center;
    }

    /* ── Input area ── */
    .stTextArea textarea, .stTextInput input {
        background: #2a2a2a !important;
        border: 1px solid #3a3a3a !important;
        color: #ececec !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        resize: none !important;
    }

    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #666 !important;
        box-shadow: none !important;
        outline: none !important;
    }

    .stTextArea textarea::placeholder, .stTextInput input::placeholder {
        color: #555 !important;
    }

    /* Labels above inputs */
    .stTextArea label, .stTextInput label {
        font-size: 13px !important;
        color: #888 !important;
        font-weight: 400 !important;
    }

    /* ── Chat message bubbles ── */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 12px 0 !important;
    }

    /* User bubble */
    [data-testid="stChatMessage"][data-role="user"] {
        background: #2a2a2a !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
        margin-bottom: 4px;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 14px 16px;
        text-align: center;
    }

    .metric-val {
        font-size: 22px;
        font-weight: 600;
        color: #ececec;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .metric-lbl {
        font-size: 10px;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 5px;
    }

    /* ── Suggestion output ── */
    .suggestion-box {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-left: 2px solid #ececec;
        border-radius: 0 8px 8px 0;
        padding: 18px 20px;
        font-size: 14px;
        line-height: 1.75;
        color: #d4d4d4;
        margin-top: 8px;
    }

    .suggestion-box.naive     { border-left-color: #666; }
    .suggestion-box.optimized { border-left-color: #ececec; }
    .suggestion-box.hyde      { border-left-color: #aaa; }

    /* ── Pipeline header ── */
    .pipeline-header {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        padding: 8px 14px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #888;
        text-align: center;
        margin-bottom: 14px;
    }

    .ph-naive     { border-left: 2px solid #666; }
    .ph-optimized { border-left: 2px solid #ececec; }
    .ph-hyde      { border-left: 2px solid #aaa; }

    /* ── HyDE box ── */
    .hyde-box {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 14px;
        font-size: 12px;
        color: #888;
        font-style: italic;
        line-height: 1.6;
        margin-bottom: 14px;
    }

    .hyde-label {
        font-size: 10px;
        font-weight: 600;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
        font-style: normal;
    }

    /* ── Impact cells ── */
    .impact-cell {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }

    .impact-big {
        font-size: 28px;
        font-weight: 700;
        color: #ececec;
        letter-spacing: -0.02em;
    }

    .impact-sub {
        font-size: 10px;
        color: #555;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 4px;
    }

    .impact-delta {
        font-size: 11px;
        color: #555;
        margin-top: 3px;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        gap: 4px;
        border-bottom: 1px solid #2a2a2a;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: #555 !important;
        font-size: 13px !important;
        padding: 8px 14px !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stTabs [aria-selected="true"] {
        color: #ececec !important;
        border-bottom: 2px solid #ececec !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: #1a1a1a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 6px !important;
        color: #888 !important;
        font-size: 12px !important;
    }

    /* ── Divider ── */
    hr { border-color: #2a2a2a !important; }

    /* ── Sliders & toggles ── */
    .stSlider [data-baseweb="slider"] { margin-top: 4px; }

    [data-testid="stToggleLabel"] {
        color: #b0b0b0 !important;
        font-size: 13px !important;
    }

    /* ── Radio ── */
    .stRadio label {
        color: #b0b0b0 !important;
        font-size: 13px !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #2a2a2a !important;
        border-radius: 8px !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #171717; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #444; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
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
def render_metrics(data):
    opt = data.get("optimization", {})
    cols = st.columns(4)
    vals = [
        (f"{data.get('total_latency_ms', 0):.0f}ms", "Total Latency"),
        (str(data.get("tokens_used", 0)),             "Tokens Used"),
        (f"{opt.get('token_savings_pct', 0)}%",       "Token Savings"),
        (str(opt.get("final_chunks", 0)),             "Chunks Used"),
    ]
    for col, (val, lbl) in zip(cols, vals):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{val}</div>
            <div class="metric-lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)


def render_latency_breakdown(data):
    stages = {
        "Retrieval":   data.get("retrieval_latency_ms", 0),
        "HyDE":        data.get("hyde_latency_ms", 0),
        "Reranking":   data.get("rerank_latency_ms", 0),
        "MMR":         data.get("mmr_latency_ms", 0),
        "Compression": data.get("compression_latency_ms", 0),
        "LLM":         data.get("llm_latency_ms", 0),
    }
    stages = {k: v for k, v in stages.items() if v > 0}
    if not stages:
        st.markdown('<p style="color:#555;font-size:13px">No latency data available.</p>', unsafe_allow_html=True)
        return

    shades = ["#ececec", "#b0b0b0", "#888", "#666", "#444", "#333"]
    colors = [shades[i % len(shades)] for i in range(len(stages))]

    fig = go.Figure(go.Bar(
        x=list(stages.values()),
        y=list(stages.keys()),
        orientation='h',
        marker_color=colors,
        text=[f"{v:.0f}ms" for v in stages.values()],
        textposition='outside',
        textfont=dict(color='#888', size=11),
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888', size=11, family='Inter'),
        margin=dict(l=10, r=80, t=10, b=10),
        height=max(140, len(stages) * 38),
        xaxis=dict(showgrid=False, showticklabels=False, color='#555'),
        yaxis=dict(showgrid=False, color='#888'),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_suggestion(text, variant="default"):
    css_class = {
        "naive":     "suggestion-box naive",
        "optimized": "suggestion-box optimized",
        "hyde":      "suggestion-box hyde",
    }.get(variant, "suggestion-box")
    safe_text = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    st.markdown(f'<div class="{css_class}">{safe_text}</div>', unsafe_allow_html=True)


def render_hyde_hypothesis(opt):
    hyp = opt.get("hyde_hypothesis", "")
    if hyp:
        safe = hyp.replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(f"""
        <div class="hyde-box">
            <div class="hyde-label">HyDE Hypothetical Document</div>
            {safe}
        </div>""", unsafe_allow_html=True)


def render_chunks(chunks):
    for i, chunk in enumerate(chunks):
        score      = chunk.get("rerank_score", 0)
        quality    = "High" if score >= 5 else ("Mid" if score >= 0 else "Low")
        compressed = chunk.get("compressed_text", "")
        original   = chunk.get("original_text", "")
        savings    = round((1 - len(compressed) / max(len(original), 1)) * 100)
        tokens     = chunk.get("tokens_used", 0)

        with st.expander(f"Ref {i+1}  ·  Abstract {chunk.get('abstract_id','')}  ·  {quality} relevance  ·  {tokens} tokens"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<p style="font-size:12px;color:#888;margin-bottom:6px">Sent to LLM</p>', unsafe_allow_html=True)
                st.markdown(f'<div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:12px;font-size:12px;color:#d4d4d4;line-height:1.7">{compressed}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<p style="font-size:12px;color:#888;margin-bottom:6px">Original ({savings}% compressed)</p>', unsafe_allow_html=True)
                st.markdown(f'<div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:6px;padding:12px;font-size:12px;color:#555;line-height:1.7">{original}</div>', unsafe_allow_html=True)


def render_pipeline_result(data, variant="default", label=""):
    ph_class = {"naive": "ph-naive", "optimized": "ph-optimized", "hyde": "ph-hyde"}.get(variant, "ph-optimized")
    if label:
        st.markdown(f'<div class="pipeline-header {ph_class}">{label}</div>', unsafe_allow_html=True)

    render_metrics(data)

    opt = data.get("optimization", {})
    tab1, tab2, tab3 = st.tabs(["Suggestion", "Latency", "Chunks"])
    with tab1:
        if variant == "hyde":
            render_hyde_hypothesis(opt)
        render_suggestion(data.get("suggestion", ""), variant)
    with tab2:
        render_latency_breakdown(data)
    with tab3:
        render_chunks(data.get("chunks", []))


def render_comparison_chart(results: dict):
    labels    = list(results.keys())
    latencies = [r.get("total_latency_ms", 0) for r in results.values()]
    tokens    = [r.get("tokens_used", 0) for r in results.values()]

    shades = ["#ececec", "#888", "#444"][:len(labels)]

    fig = go.Figure(data=[
        go.Bar(name="Latency (ms)", x=labels, y=latencies,
               marker_color=shades, opacity=0.9,
               yaxis="y", offsetgroup=0),
        go.Bar(name="Tokens", x=labels, y=tokens,
               marker_color=shades, opacity=0.5,
               yaxis="y2", offsetgroup=1),
    ])
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888', size=11, family='Inter'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#888', size=11)),
        margin=dict(l=10, r=10, t=20, b=10),
        height=260,
        yaxis=dict(showgrid=True, gridcolor='#2a2a2a', title="Latency (ms)",
                   title_font=dict(size=10, color='#555'), color='#555'),
        yaxis2=dict(overlaying='y', side='right', title="Tokens",
                    title_font=dict(size=10, color='#555'), showgrid=False, color='#555'),
        xaxis=dict(showgrid=False, color='#888'),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-title">Rapid Remedy</div>
        <div class="sb-logo-sub">Clinical RAG · Vector Search Benchmark</div>
    </div>
    """, unsafe_allow_html=True)

    # API status
    health = call_health()
    if health:
        count_str = health.get("db", "").split("(")[-1].replace(")", "").strip() \
                    if "(" in health.get("db", "") else ""
        st.markdown(f"""
        <div class="status-badge status-online">
            <span class="status-dot-on">&#9679;</span>  API Connected
            <span style="display:block;font-size:11px;color:#555;margin-top:2px">{count_str}</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-badge status-offline">
            <span class="status-dot-off">&#9679;</span>  API Offline
        </div>""", unsafe_allow_html=True)

    # ── Settings ──
    st.markdown('<div class="section-label">Settings</div>', unsafe_allow_html=True)
    top_k           = st.slider("Top-K chunks", 1, 10, 5)
    use_reranking   = st.toggle("Cross-encoder reranking", value=True)
    use_compression = st.toggle("Context compression", value=True)
    use_hyde        = st.toggle("HyDE query expansion", value=False,
                                help="Generates a hypothetical clinical abstract from your symptoms, then embeds it for retrieval.")
    use_mmr         = st.toggle("MMR diversity filter", value=False,
                                help="Maximal Marginal Relevance — selects diverse chunks instead of near-duplicates.")

    st.markdown('<div class="section-label">Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "mode",
        ["Single Query", "Naive vs Optimized", "Full Pipeline Compare"],
        label_visibility="collapsed"
    )

    # ── History ──
    st.markdown('<div class="section-label">History</div>', unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown('<p style="color:#444;font-size:12px;padding:4px 2px">No queries yet</p>', unsafe_allow_html=True)
    else:
        for i, session in enumerate(reversed(st.session_state.chat_history)):
            idx = len(st.session_state.chat_history) - 1 - i
            preview = session["symptoms"][:40] + "..." if len(session["symptoms"]) > 40 else session["symptoms"]
            if st.button(preview, key=f"hist_{idx}", use_container_width=True):
                st.session_state.active_session = idx
                st.rerun()
            st.markdown(f'<p style="font-size:10px;color:#444;margin:-4px 0 6px 2px">{session.get("timestamp","")} · {session.get("mode_label","")}</p>', unsafe_allow_html=True)

        if st.button("Clear history", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.active_session = None
            st.rerun()

    # ── Dataset chart ──
    stats = call_stats()
    if stats:
        st.markdown('<div class="section-label">Dataset</div>', unsafe_allow_html=True)
        dist = stats.get("label_distribution", [])
        if dist:
            df_dist = pd.DataFrame(dist)
            fig = px.bar(df_dist, x="count", y="label", orientation='h',
                         color_discrete_sequence=["#ececec"])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#555', size=9, family='Inter'),
                margin=dict(l=0, r=0, t=0, b=0),
                height=180,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, title="", color='#888'),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-title">Rapid Remedy</div>
    <div class="hero-sub">Medical RAG · Vector Search Benchmark · v4.0</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="warn-bar">
    Research purposes only — always consult a licensed physician for medical decisions.
</div>
""", unsafe_allow_html=True)


# ── Active session replay ──────────────────────────────────────────────────────
if st.session_state.active_session is not None:
    idx = st.session_state.active_session
    if 0 <= idx < len(st.session_state.chat_history):
        session = st.session_state.chat_history[idx]

        st.markdown(f"""
        <div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;
                    padding:14px 18px;margin-bottom:20px">
            <div style="font-size:10px;color:#555;margin-bottom:6px;text-transform:uppercase;
                        letter-spacing:0.08em">
                Saved · {session.get('timestamp','')} · {session.get('mode_label','')}
            </div>
            <div style="font-size:15px;color:#ececec;font-weight:500">{session['symptoms']}</div>
            {f'<div style="font-size:13px;color:#888;margin-top:4px">{session["patient_context"]}</div>'
              if session.get("patient_context") else ""}
        </div>""", unsafe_allow_html=True)

        col_back, _ = st.columns([1, 5])
        with col_back:
            if st.button("Back to new query"):
                st.session_state.active_session = None
                st.rerun()

        stored = session.get("results", {})
        if "single" in stored:
            st.markdown("---")
            render_pipeline_result(stored["single"], "optimized", "")
        elif "naive" in stored and "opt" in stored:
            st.markdown("---")
            st.markdown('<div class="section-label">Performance Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({"Naive": stored["naive"], "Optimized": stored["opt"]})
            c1, c2 = st.columns(2)
            with c1:
                render_pipeline_result(stored["naive"], "naive", "Naive RAG")
            with c2:
                render_pipeline_result(stored["opt"], "optimized", "Optimized RAG")
        st.stop()


# ── Input form ─────────────────────────────────────────────────────────────────
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    symptoms = st.text_area(
        "Patient symptoms",
        placeholder="e.g. chest pain, shortness of breath, diaphoresis, radiating left arm pain...",
        height=96,
    )
with col_in2:
    patient_context = st.text_area(
        "Patient context (optional)",
        placeholder="e.g. 55yo male, smoker, hypertension...",
        height=96,
    )

run = st.button("Run clinical query", use_container_width=True, type="primary")


# ── Mode: Single Query ─────────────────────────────────────────────────────────
if mode == "Single Query" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        active_flags = []
        if use_reranking:   active_flags.append("rerank")
        if use_compression: active_flags.append("compress")
        if use_hyde:        active_flags.append("HyDE")
        if use_mmr:         active_flags.append("MMR")

        with st.spinner("Running pipeline..."):
            data, err = call_query(symptoms, patient_context, top_k,
                                   use_reranking, use_compression, use_hyde, use_mmr)
        if err:
            st.error(f"Error: {err}")
        else:
            st.session_state.chat_history.append({
                "symptoms": symptoms,
                "patient_context": patient_context,
                "timestamp": datetime.now().strftime("%H:%M"),
                "mode_label": "single · " + ("+".join(active_flags) if active_flags else "base"),
                "results": {"single": data},
            })

            st.markdown("---")
            variant = "hyde" if use_hyde else "optimized"
            render_pipeline_result(data, variant, "")


# ── Mode: Naive vs Optimized ───────────────────────────────────────────────────
elif mode == "Naive vs Optimized" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        with st.spinner("Running both pipelines..."):
            naive_data, naive_err = call_query(symptoms, patient_context, top_k,
                                               False, False, False, False)
            opt_data, opt_err = call_query(symptoms, patient_context, top_k,
                                           True, True, False, False)
        if naive_err or opt_err:
            st.error(naive_err or opt_err)
        else:
            st.session_state.chat_history.append({
                "symptoms": symptoms,
                "patient_context": patient_context,
                "timestamp": datetime.now().strftime("%H:%M"),
                "mode_label": "A/B compare",
                "results": {"naive": naive_data, "opt": opt_data},
            })

            st.markdown("---")
            st.markdown('<div class="section-label">Performance Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({"Naive": naive_data, "Optimized": opt_data})

            c1, c2 = st.columns(2)
            with c1:
                render_pipeline_result(naive_data, "naive", "Naive RAG")
            with c2:
                render_pipeline_result(opt_data, "optimized", "Optimized RAG")

            # Impact summary
            st.markdown("---")
            st.markdown('<div class="section-label">Optimization Impact</div>', unsafe_allow_html=True)

            n_tok = naive_data.get("tokens_used", 1)
            o_tok = opt_data.get("tokens_used", 1)
            n_lat = naive_data.get("total_latency_ms", 1)
            o_lat = opt_data.get("total_latency_ms", 1)
            tok_delta  = round((1 - o_tok / n_tok) * 100, 1)
            lat_delta  = round((1 - o_lat / n_lat) * 100, 1)
            tok_saved  = n_tok - o_tok
            rerank_in  = opt_data.get("optimization", {}).get("candidates_retrieved", 0)
            rerank_out = opt_data.get("optimization", {}).get("final_chunks", 0)

            col1, col2, col3 = st.columns(3)
            col1.markdown(f"""
            <div class="impact-cell">
                <div class="impact-big">{tok_delta}%</div>
                <div class="impact-sub">Token Reduction</div>
                <div class="impact-delta">{tok_saved} tokens saved</div>
            </div>""", unsafe_allow_html=True)
            col2.markdown(f"""
            <div class="impact-cell">
                <div class="impact-big">{lat_delta:+.1f}%</div>
                <div class="impact-sub">Latency Change</div>
                <div class="impact-delta">{abs(n_lat - o_lat):.0f}ms difference</div>
            </div>""", unsafe_allow_html=True)
            col3.markdown(f"""
            <div class="impact-cell">
                <div class="impact-big">{rerank_in}&rarr;{rerank_out}</div>
                <div class="impact-sub">Reranking Filter</div>
                <div class="impact-delta">candidates to final chunks</div>
            </div>""", unsafe_allow_html=True)


# ── Mode: Full Pipeline Compare ────────────────────────────────────────────────
elif mode == "Full Pipeline Compare" and run:
    if not symptoms.strip():
        st.error("Please enter patient symptoms.")
    else:
        with st.spinner("Running all three pipelines..."):
            naive_data, naive_err = call_query(symptoms, patient_context, top_k,
                                               False, False, False, False)
            opt_data, opt_err     = call_query(symptoms, patient_context, top_k,
                                               True, True, False, False)
            hyde_data, hyde_err   = call_query(symptoms, patient_context, top_k,
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
            st.markdown('<div class="section-label">Three-Pipeline Comparison</div>', unsafe_allow_html=True)
            render_comparison_chart({
                "Naive":     naive_data,
                "Optimized": opt_data,
                "HyDE+MMR":  hyde_data,
            })

            c1, c2, c3 = st.columns(3)
            with c1:
                render_pipeline_result(naive_data, "naive",     "Naive RAG")
            with c2:
                render_pipeline_result(opt_data,   "optimized", "Optimized RAG")
            with c3:
                render_pipeline_result(hyde_data,  "hyde",      "HyDE + MMR")

            # 3-way benchmark table
            st.markdown("---")
            st.markdown('<div class="section-label">Benchmark Results</div>', unsafe_allow_html=True)

            rows = []
            for name, d in {"Naive": naive_data, "Optimized": opt_data, "HyDE+MMR": hyde_data}.items():
                opt = d.get("optimization", {})
                rows.append({
                    "Pipeline":        name,
                    "Latency (ms)":    round(d.get("total_latency_ms", 0)),
                    "Tokens":          d.get("tokens_used", 0),
                    "Token Savings %": opt.get("token_savings_pct", 0),
                    "Chunks Used":     opt.get("final_chunks", 0),
                    "Retrieval (ms)":  round(d.get("retrieval_latency_ms", 0), 1),
                    "HyDE (ms)":       round(d.get("hyde_latency_ms", 0), 1),
                    "Rerank (ms)":     round(d.get("rerank_latency_ms", 0), 1),
                    "MMR (ms)":        round(d.get("mmr_latency_ms", 0), 1),
                    "LLM (ms)":        round(d.get("llm_latency_ms", 0), 1),
                })
            df_bench = pd.DataFrame(rows)
            st.dataframe(df_bench, use_container_width=True, hide_index=True)