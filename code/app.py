"""
EngageIQ — Smart Engagement Opportunity Scorer
BAX-423 · Spring 2026 · Preksha Raval
"""
import streamlit as st
import json, os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── page config first ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EngageIQ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 3D glassmorphism dark theme ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --bg:        #0a0b0f;
  --surface:   #15171f;
  --glass:     #15171f;
  --glass-b:   #2a2d3a;
  --accent:    #818cf8;
  --accent2:   #c4b5fd;
  --accent3:   #fbbf24;
  --text:      #f3f4f6;
  --muted:     #a1a8b5;
  --success:   #34d399;
  --danger:    #f87171;
  --surface-2: #1c1f29;
  --grad:      linear-gradient(135deg,#818cf8,#c4b5fd);
}

html, body, [data-testid="stApp"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif;
}

/* sidebar */
[data-testid="stSidebar"] {
  background: #0f1117 !important;
  border-right: 1px solid var(--glass-b) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* header */
.eq-header { text-align:center; padding: 2.5rem 1rem 1.25rem; position:relative; }
.eq-header h1 {
  font-family:'Space Grotesk',sans-serif; font-size:3.4rem; font-weight:700;
  letter-spacing:-1.5px;
  background: linear-gradient(90deg,#818cf8,#c4b5fd);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  margin:0; line-height:1;
}
.eq-header p {
  color: var(--muted); font-family:'Inter',sans-serif; font-size:0.74rem; font-weight:500;
  margin-top:0.65rem; letter-spacing:2.5px; text-transform:uppercase;
}

/* card */
.eq-card {
  background: var(--surface); border:1px solid var(--glass-b);
  border-radius:14px; padding:1.25rem 1.5rem; margin-bottom:1rem;
  transition: all 0.2s ease; position:relative; overflow:hidden;
}
.eq-card:hover {
  border-color:#3d4152; box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  transform: translateY(-1px);
}

/* rank badge */
.rank-badge { display:inline-flex; align-items:center; justify-content:center;
  width:32px; height:32px; border-radius:50%; font-family:'Space Grotesk',sans-serif;
  font-weight:700; font-size:0.8rem; flex-shrink:0; }
.rank-1 { background: linear-gradient(135deg,#fbbf24,#f87171); color:#1a1a1a; }
.rank-2 { background: linear-gradient(135deg,#cbd5e1,#94a3b8); color:#1a1a1a; }
.rank-3 { background: linear-gradient(135deg,#fbbf24,#d97706); color:#1a1a1a; }
.rank-n { background: #262936; color: var(--muted); }

/* score */
.score-ring { display:flex; flex-direction:column; align-items:center; gap:2px; }
.score-val { font-family:'Space Grotesk',sans-serif; font-size:1.45rem; font-weight:700; color: var(--accent); line-height:1; }
.score-lbl { font-size:0.62rem; color: var(--muted); letter-spacing:1px; text-transform:uppercase; }

/* source chip */
.chip { display:inline-block; padding:2px 10px; border-radius:999px;
  font-family:'Inter',sans-serif; font-size:0.68rem; font-weight:600;
  letter-spacing:0.3px; text-transform:uppercase; }
.chip-github    { background:rgba(129,140,248,0.18); color:#a5b4fc; border:1px solid rgba(129,140,248,0.4); }
.chip-hackernews{ background:rgba(251,191,36,0.16); color:#fcd34d; border:1px solid rgba(251,191,36,0.4); }
.chip-reddit    { background:rgba(248,113,113,0.16); color:#fca5a5; border:1px solid rgba(248,113,113,0.4); }

/* domain tag */
.domain-tag { display:inline-block; padding:2px 8px; border-radius:6px; font-size:0.65rem;
  background:rgba(129,140,248,0.14); color:#a5b4fc; border:1px solid rgba(129,140,248,0.3); font-family:'Inter',sans-serif; }

.action-row { display:flex; gap:8px; margin-top:0.75rem; }

/* why panel */
.why-bar-wrap { margin:0.5rem 0; }
.why-label { font-size:0.72rem; color: var(--muted); margin-bottom:2px; font-family:'Inter',sans-serif; }
.why-bar-bg { background:rgba(255,255,255,0.08); border-radius:4px; height:8px; overflow:hidden; }
.why-bar-fill { height:100%; border-radius:4px; transition: width 0.6s ease; }

/* metric pill */
.metric-pill { display:inline-flex; align-items:center; gap:6px; padding:4px 12px;
  border-radius:999px; background:var(--surface-2); border:1px solid var(--glass-b);
  font-size:0.72rem; font-family:'Inter',sans-serif; color: var(--text); }

/* tabs */
.stTabs [data-baseweb="tab-list"] { background:var(--surface-2); border-radius:12px; padding:4px; gap:4px; border:1px solid var(--glass-b); }
.stTabs [data-baseweb="tab"] { border-radius:8px !important; color: var(--muted) !important; font-family:'Space Grotesk',sans-serif !important; font-weight:600 !important; font-size:0.85rem !important; }
.stTabs [aria-selected="true"] { background:rgba(129,140,248,0.16) !important; color: #c4b5fd !important; border:1px solid rgba(129,140,248,0.35) !important; }

/* inputs */
.stSelectbox > div, .stMultiSelect > div, .stSlider, .stTextArea textarea {
  background:var(--surface-2) !important; border:1px solid var(--glass-b) !important; border-radius:10px !important; color: var(--text) !important; }
.stTextArea textarea { background:var(--surface-2) !important; color: var(--text) !important; }

/* buttons */
.stButton button { background:var(--surface-2) !important; border:1px solid var(--glass-b) !important; color: #c4b5fd !important; border-radius:8px !important; font-family:'Inter',sans-serif !important; font-weight:600 !important; font-size:0.78rem !important; transition: all 0.2s !important; }
.stButton button:hover { background:rgba(129,140,248,0.16) !important; border-color: var(--accent) !important; transform: translateY(-1px) !important; }

/* misc */
.stMarkdown h3 { font-family:'Space Grotesk',sans-serif; font-size:1rem; color: var(--text); }
hr { border-color: var(--glass-b) !important; }
.stSpinner { color: var(--accent) !important; }
[data-testid="stMetric"] { background:var(--surface); border-radius:12px; padding:0.85rem 1rem; border:1px solid var(--glass-b); }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family:'Space Grotesk',sans-serif !important; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size:0.72rem !important; }
</style>
""", unsafe_allow_html=True)

# ── imports ──────────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(__file__))
from score.composite import Ranker, WEIGHTS
from learn.bandit import load_bandit, make_rerank_fn, record_feedback
from analytics import trends as T
from export.brief import build_brief_pdf, build_csv
from llm.suggest_action import suggest_action
from common import connect, get_logger
import monitoring

log = get_logger("engageiq.app")


def validate_profile(interests, free_text, time_budget):
    """Trust nothing (Lecture 10: input validation everywhere). Returns a list of
    human-readable problems; empty list means the profile is safe to score."""
    problems = []
    if not interests:
        problems.append("Pick at least one domain.")
    if len(interests) > 15:
        problems.append("Too many domains selected.")
    if free_text and len(free_text) > 2000:
        problems.append("Goal text is too long (max 2000 chars).")
    if not (1 <= int(time_budget) <= 40):
        problems.append("Time budget must be between 1 and 40 hours.")
    return problems


DOMAIN_LABELS = {
    "ml": "Machine Learning", "devops_k8s": "DevOps/K8s",
    "trending_oss": "Trending Open-Source", "developer_tools": "Developer Tools",
    "cybersecurity": "Cybersecurity", "frontend_web": "Frontend (React/Web)",
    "b2b_saas": "B2B SaaS", "blockchain": "Blockchain",
    "python_data_eng": "Python Data Eng", "gamedev_cpp": "GameDev (C++)",
    "ai_research": "AI Research", "embedded_systems": "Embedded Systems (C/RTOS)",
    "cloud_apis": "Cloud APIs", "mobile_dev": "Mobile Dev (iOS/Flutter)",
    "beginner_coding": "Beginner Coding",
}

SOURCE_COLORS = {"github": "chip-github", "hackernews": "chip-hackernews", "reddit": "chip-reddit"}
SOURCE_ICONS  = {"github": "⬡", "hackernews": "◈", "reddit": "◉"}
COMP_COLORS   = {
    "relevance":          "#818cf8",
    "community_health":   "#c4b5fd",
    "visibility_potential":"#f59e0b",
    "effort_inv":         "#10b981",
}
COMP_LABELS = {
    "relevance": "Relevance", "community_health": "Community",
    "visibility_potential": "Visibility", "effort_inv": "Low Effort",
}

@st.cache_resource
def get_ranker():
    return Ranker()

def score_color(s):
    if s >= 0.75: return "#10b981"
    if s >= 0.55: return "#f59e0b"
    return "#ef4444"

def render_why(components):
    total = sum(components.values()) or 1
    for k, v in components.items():
        pct = int(v / max(total, 1e-6) * 100)
        bar_w = int(v * 100)
        color = COMP_COLORS.get(k, "#64748b")
        lbl = COMP_LABELS.get(k, k)
        st.markdown(f"""
        <div class="why-bar-wrap">
          <div class="why-label">{lbl} — {v:.3f} ({pct}%)</div>
          <div class="why-bar-bg">
            <div class="why-bar-fill" style="width:{bar_w}%;background:{color};"></div>
          </div>
        </div>""", unsafe_allow_html=True)

def opp_card(opp, rank):
    score = opp.get("final", opp["composite"])
    sc = score_color(score)
    src = opp["source"]
    domain = opp.get("domain","")
    badge_cls = f"rank-{rank}" if rank <= 3 else "rank-n"
    chip_cls  = SOURCE_COLORS.get(src, "chip-github")
    icon      = SOURCE_ICONS.get(src, "○")
    domain_lbl = DOMAIN_LABELS.get(domain, domain)

    st.markdown(f"""
    <div class="eq-card float-anim" style="animation-delay:{rank*0.1}s">
      <div style="display:flex;align-items:flex-start;gap:14px;">
        <div><span class="rank-badge {badge_cls}">#{rank}</span></div>
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
            <span class="chip {chip_cls}">{icon} {src}</span>
            <span class="domain-tag">{domain_lbl}</span>
          </div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1rem;
                      color:#f1f5f9;margin-bottom:4px;line-height:1.3;">
            {opp['title'][:120]}
          </div>
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:6px;">
            <span class="metric-pill">⭐ {opp.get('score_raw',0):,}</span>
            <span class="metric-pill">💬 {opp.get('num_comments',0)}</span>
            <span class="metric-pill">⚡ vel {opp.get('velocity',0):.2f}</span>
            <span class="metric-pill">🎯 effort {opp.get('effort',0.5):.2f}</span>
          </div>
        </div>
        <div class="score-ring">
          <div class="score-val" style="color:{sc};">{score:.3f}</div>
          <div class="score-lbl">score</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    with st.expander("🔍 Why this? · Suggested action · Feedback"):
        c1, c2 = st.columns([1,1])
        with c1:
            st.markdown("**Score breakdown**")
            render_why(opp.get("components", {}))
        with c2:
            st.markdown("**Suggested action**")
            action = suggest_action(opp)
            st.markdown(f"""<div style="background:rgba(129,140,248,0.10);border-left:3px solid var(--accent);
                            border-radius:8px;padding:10px 14px;font-size:0.82rem;line-height:1.5;
                            color:#cbd5e1;">{action}</div>""", unsafe_allow_html=True)
            url = opp.get('url','')
            is_synth = 'synth' in url or (opp.get('author','') or '').startswith('synth_')
            if url and not is_synth:
                st.markdown(f"[🔗 View on {src}]({url})")
            else:
                st.caption("📡 Sample HN/Reddit record — this build ships a snapshot; "
                           "live API ingestion is built in (see the Methods tab).")
        st.markdown("**Your feedback** *(trains the bandit)*")
        uid = st.session_state.get("user_id","guest")
        cols = st.columns(3)
        if cols[0].button("✅ Engage",   key=f"eng_{opp['id']}"): record_feedback(uid, opp, "engage");   st.rerun()
        if cols[1].button("🔖 Bookmark", key=f"bkm_{opp['id']}"): record_feedback(uid, opp, "bookmark"); st.rerun()
        if cols[2].button("⏭ Skip",     key=f"skp_{opp['id']}"): record_feedback(uid, opp, "skip");     st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style="text-align:center;padding:1rem 0 0.5rem;">
      <div style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:800;
                  background:linear-gradient(90deg,#818cf8,#c4b5fd);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;">⚡ EngageIQ</div>
      <div style="font-family:'Inter',sans-serif;font-size:0.65rem;
                  color:#a1a8b5;letter-spacing:2px;text-transform:uppercase;">
        opportunity scorer
      </div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    user_id = st.text_input("Your name", value="preksha", placeholder="any name",
                            help="Used only to remember your Engage/Skip feedback so results personalize for you.")
    st.session_state["user_id"] = user_id

    interests = st.multiselect(
        "What do you work on?", options=list(DOMAIN_LABELS.keys()),
        format_func=lambda k: DOMAIN_LABELS[k],
        default=["ml", "ai_research", "developer_tools"],
        help="Pick the technical areas you want opportunities in.",
    )
    free_text = st.text_area("Your goal (optional)", placeholder="e.g. I want to contribute to ML projects and build my GitHub portfolio...", height=90,
                             help="A sentence about what you're trying to do. Sharpens the ranking.")
    time_budget = st.slider("⏱ Hours per week", 1, 20, 5,
                            help="How much time you have. Used to fit the weekly plan to your schedule.")
    platforms = st.multiselect("Where to look", ["github","hackernews","reddit"],
                               default=["github","hackernews","reddit"],
                               help="Which sources to pull opportunities from.")
    topn = st.slider("How many results", 5, 30, 10)
    adaptive = st.toggle("🧠 Personalize from my feedback", value=True,
                         help="Learns from your Engage/Bookmark/Skip clicks to reorder results "
                              "(a LinUCB contextual bandit — BAX-423 Lecture 8).")
    diversify = st.toggle("🎨 Mix up the results", value=True,
                          help="Keeps the list varied instead of ten near-identical items "
                               "(diversity re-ranking — BAX-423 Lecture 6).")

    st.divider()
    st.markdown("<div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;'>BAX-423 · Spring 2026<br>UC Davis GSM</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<div class="eq-header">
  <h1>EngageIQ</h1>
  <p>Where should you show up online to grow your tech career?</p>
</div>""", unsafe_allow_html=True)

# ── plain-language intro + how it works (so a first-time viewer gets it instantly) ──
st.markdown("""
<div style="max-width:920px;margin:0 auto 1.25rem;">
  <div style="background:var(--surface);border:1px solid var(--glass-b);border-radius:14px;
              padding:1.1rem 1.4rem;color:var(--text);font-family:'Inter',sans-serif;
              font-size:0.92rem;line-height:1.65;">
    <span style="color:var(--accent);font-weight:700;">What is this?</span>
    Every week there are thousands of places a developer <i>could</i> engage online &mdash; open-source
    issues to fix, Hacker News threads to weigh in on, Reddit questions to answer &mdash; but no easy way
    to know which are worth the time. <b>EngageIQ indexes opportunities from GitHub, Hacker News, and Reddit across 15 technical domains — 865 real GitHub records from the API, plus realistic synthetic data for HN and Reddit — then ranks the ones that fit your skills and weekly hours</b> and explains <i>why</i> each made the list.
  </div>
  <div style="display:flex;gap:10px;margin-top:0.7rem;flex-wrap:wrap;">
""" + "".join([
    f"""<div style="flex:1;min-width:170px;background:var(--surface-2);border:1px solid var(--glass-b);
            border-radius:10px;padding:0.6rem 0.8rem;font-size:0.78rem;color:var(--muted);
            font-family:'Inter',sans-serif;line-height:1.4;">
      <span style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;
            border-radius:50%;background:rgba(129,140,248,0.18);color:#a5b4fc;font-weight:700;
            margin-right:6px;">{n}</span>{txt}</div>"""
    for n, txt in [
        (1, "Set your domains &amp; weekly hours in the sidebar"),
        (2, "EngageIQ ranks 10,995 indexed opportunities for you"),
        (3, "See <i>why</i> each was picked, plus a suggested action"),
        (4, "Engage / Skip to teach it your taste over time"),
    ]
]) + """
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Discover", "📈 Trends", "📄 Brief", "🔬 Methods"])

# ── TAB 1: DISCOVER ──────────────────────────────────────────────────────────
with tab1:
    if not interests:
        st.markdown("""<div class="eq-card" style="text-align:center;padding:2rem;">
          <div style="font-size:2rem;">👈</div>
          <div style="color:var(--text);font-family:'Inter',sans-serif;font-size:0.95rem;margin-top:0.5rem;font-weight:600;">
            Pick a few domains in the sidebar to get started
          </div>
          <div style="color:var(--muted);font-family:'Inter',sans-serif;font-size:0.8rem;margin-top:0.35rem;">
            Choose what you work on (e.g. Machine Learning, DevOps), set your weekly hours,
            and EngageIQ will rank the best places to engage this week.
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        problems = validate_profile(interests, free_text, time_budget)
        if problems:
            for p in problems:
                st.warning(p)
            st.stop()

        cold = False
        try:
            with st.spinner("⚡ Scoring opportunities..."):
                ranker = get_ranker()
                rerank_fn = None
                if adaptive:
                    bandit = load_bandit(user_id)
                    cold = bandit.is_cold
                    rerank_fn = make_rerank_fn(bandit)
                results = ranker.rank(
                    interests=interests, free_text=free_text,
                    platforms=platforms, topn=topn,
                    rerank_fn=rerank_fn, diversity=diversify,
                )
        except Exception:
            # Generic message to the user; full traceback to the logs (Lecture 10).
            log.exception("ranking_failed user=%s interests=%s", user_id, interests)
            st.error("Something went wrong while scoring. Please adjust your profile and try again.")
            st.stop()

        if not results:
            st.warning("No opportunities found. Try adding more domains or platforms.")
        else:
            if adaptive and cold:
                st.info("🌱 **Cold start** — you haven't given feedback yet, so rankings lean on "
                        "the composite score. Use the Engage / Bookmark / Skip buttons and the "
                        "bandit will personalize as it learns.")
            elif adaptive:
                st.success(f"🧠 **Personalized** — adapting to your feedback "
                           f"(bandit trust {bandit.trust():.0%}).")
            # Summary metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Opportunities", len(results))
            m2.metric("Avg Score", f"{sum(r.get('final',r['composite']) for r in results)/len(results):.3f}")
            m3.metric("Top Score",  f"{max(r.get('final',r['composite']) for r in results):.3f}")
            m4.metric("Sources",    len(set(r['source'] for r in results)))

            st.divider()

            # 3D scatter mini-viz
            if len(results) >= 3:
                fig = go.Figure(data=[go.Scatter3d(
                    x=[r["components"]["relevance"] for r in results],
                    y=[r["components"]["community_health"] for r in results],
                    z=[r["components"]["visibility_potential"] for r in results],
                    mode="markers+text",
                    text=[f"#{i+1}" for i in range(len(results))],
                    marker=dict(
                        size=8,
                        color=[r.get("final",r["composite"]) for r in results],
                        colorscale=[[0,"#818cf8"],[0.5,"#c4b5fd"],[1,"#fbbf24"]],
                        opacity=0.85,
                        line=dict(width=1, color="rgba(255,255,255,0.25)"),
                    ),
                    textfont=dict(color="#f3f4f6", size=9),
                )])
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0,r=0,t=30,b=0), height=300,
                    font=dict(color="#d1d5db", family="Inter"),
                    scene=dict(
                        bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(title="Relevance", color="#9ca3af", gridcolor="#2a2d3a"),
                        yaxis=dict(title="Community", color="#9ca3af", gridcolor="#2a2d3a"),
                        zaxis=dict(title="Visibility", color="#9ca3af", gridcolor="#2a2d3a"),
                    ),
                    title=dict(text="3D opportunity space", font=dict(color="#818cf8", size=12, family="Inter"), x=0.5),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.divider()
            for i, opp in enumerate(results):
                opp_card(opp, i + 1)

# ── TAB 2: TRENDS ────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📈 Trending Topics")
    kw = T.trending_keywords(top=12)
    if not kw.empty:
        fig_kw = px.bar(kw.sort_values("estimated_freq"), x="estimated_freq", y="keyword",
                        orientation="h",
                        color="estimated_freq",
                        color_continuous_scale=[[0,"#4f46e5"],[1,"#818cf8"]],
                        labels={"estimated_freq":"Count-Min estimate","keyword":""})
        fig_kw.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#d1d5db", family="Inter"),
            xaxis=dict(gridcolor="#2a2d3a"), yaxis=dict(gridcolor="#2a2d3a"),
            coloraxis_showscale=False, margin=dict(l=0,r=0,t=10,b=20), height=300,
        )
        st.plotly_chart(fig_kw, use_container_width=True)
        st.caption("Keyword frequencies estimated with a Count-Min Sketch (O(1) memory, "
                   "velocity-weighted) rather than a full term-count dictionary — Lecture 2.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔥 Growing Domains")
        growing = T.growing_domains()
        if not growing.empty:
            st.dataframe(growing.style.background_gradient(cmap="Blues"), use_container_width=True, height=250)
    with c2:
        st.markdown("### 🌐 Source Mix")
        mix = T.source_mix()
        if not mix.empty:
            fig_pie = px.pie(mix, names="source", values="count",
                             color_discrete_sequence=["#818cf8","#fbbf24","#f87171"])
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color="#d1d5db"), margin=dict(l=0,r=0,t=20,b=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 📊 Volume Over Time")
    vol = T.volume_over_time(window_hours=72)
    if not vol.empty:
        fig_vol = px.area(vol, x="hour", y="count",
                          color_discrete_sequence=["#818cf8"])
        fig_vol.update_traces(fill="tozeroy", fillcolor="rgba(129,140,248,0.12)", line=dict(color="#818cf8", width=2))
        fig_vol.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#d1d5db", family="Inter"),
            xaxis=dict(gridcolor="#2a2d3a"), yaxis=dict(gridcolor="#2a2d3a"),
            margin=dict(l=0,r=0,t=10,b=40), height=220,
        )
        st.plotly_chart(fig_vol, use_container_width=True)

# ── TAB 3: BRIEF ────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 📄 Weekly Engagement Brief")
    if not interests:
        st.info("Set your profile in the sidebar first, then generate your brief.")
    else:
        profile = {"user_id": user_id, "interests": interests,
                   "time_budget": time_budget, "platforms": platforms}
        ranker2 = get_ranker()
        top10 = ranker2.rank(interests=interests, free_text=free_text,
                              platforms=platforms, topn=10)
        c1, c2 = st.columns(2)
        with c1:
            pdf = build_brief_pdf(profile, top10)
            st.download_button("⬇ Download PDF Brief", pdf,
                               file_name="engageiq_brief.pdf", mime="application/pdf",
                               use_container_width=True)
        with c2:
            csv = build_csv(top10)
            st.download_button("⬇ Download CSV", csv.encode(),
                               file_name="engageiq_opportunities.csv", mime="text/csv",
                               use_container_width=True)
        st.divider()
        st.markdown("**Top 5 preview**")
        for i, opp in enumerate(top10[:5]):
            score = opp.get("final", opp["composite"])
            src_icon = SOURCE_ICONS.get(opp["source"],"○")
            chip_cls = SOURCE_COLORS.get(opp["source"],"chip-github")
            st.markdown(f"""<div class="eq-card" style="padding:0.75rem 1rem;">
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-family:'Inter',sans-serif;color:var(--muted);font-size:0.8rem;">#{i+1}</span>
                <span class="chip {chip_cls}">{src_icon} {opp['source']}</span>
                <span style="flex:1;font-size:0.88rem;color:#e2e8f0;">{opp['title'][:90]}</span>
                <span style="font-family:'Inter',sans-serif;color:var(--accent);font-weight:700;">{score:.3f}</span>
              </div>
            </div>""", unsafe_allow_html=True)

# ── TAB 4: METHODS ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🔬 Data & Methods")
    conn = connect()
    total_rec = conn.execute("select count(*) from opportunities").fetchone()[0]
    n_domains  = conn.execute("select count(distinct domain) from opportunities").fetchone()[0]
    n_sources  = conn.execute("select count(distinct source) from opportunities").fetchone()[0]
    n_real     = conn.execute("select count(*) from opportunities where author not like 'synth_%'").fetchone()[0]
    domain_df  = pd.DataFrame(conn.execute("select domain,count(*) as n from opportunities group by domain order by n desc").fetchall(), columns=["domain","count"])
    conn.close()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Records", f"{total_rec:,}")
    m2.metric("Domains", n_domains)
    m3.metric("Sources", n_sources)
    m4.metric("Real Records", f"{n_real:,}")
    st.caption(f"📌 **Data composition:** {n_real:,} **real** GitHub records pulled live from the API "
               f"(including good-first-issue repos and issues). The remaining {total_rec - n_real:,} are "
               f"**realistic synthetic** records for Hacker News and Reddit — those APIs were "
               f"network-restricted in the build environment. The ingestion scripts in "
               f"`code/ingest/` are fully built and pull live HN/Reddit data with the right "
               f"API credentials (see `.env.example`). This is documented under Limitations in `brief.pdf`.")

    fig_dom = px.bar(domain_df, x="domain", y="count",
                     color="count", color_continuous_scale=[[0,"#4f46e5"],[1,"#818cf8"]])
    fig_dom.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="#d1d5db",family="Inter"),
                           xaxis=dict(tickangle=-35,gridcolor="#2a2d3a"),
                           yaxis=dict(gridcolor="#2a2d3a"), coloraxis_showscale=False,
                           margin=dict(l=0,r=0,t=20,b=100), height=300)
    st.plotly_chart(fig_dom, use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""**Technique 1 — FAISS Embedding Retrieval**
Opportunities and profile queries are encoded to 256-dim vectors (TF-IDF+SVD; upgrades to SBERT when available).
FAISS `IndexFlatIP` retrieves top-k by cosine similarity in ~1.3ms.
**Recall@50 = 0.99** vs TF-IDF lexical baseline 0.74.""")
    with c2:
        st.markdown("""**Technique 2 — LinUCB Contextual Bandit**
Per-user adaptive re-ranking. Context = 7-dim [relevance, community, visibility, effort⁻¹, is_github, is_reddit, is_hn].
Reward: engage +1 · bookmark +2 · skip −1. Cold-start aware (leans on composite until feedback arrives).
Bandit beats the static ranker on all 4 personas.""")

    st.divider()
    st.markdown("""**Scoring formula**
```
composite = 0.50 × relevance  +  0.20 × community_health
          + 0.20 × visibility  +  0.10 × (1 − effort)
```
**Pipeline:** stream ingest → MinHash-LSH dedup → embed → FAISS index → composite score → LinUCB rerank → dashboard""")

    st.divider()
    st.markdown("### 🩺 System Health")
    try:
        h = monitoring.health()
        hc1, hc2, hc3 = st.columns(3)
        hc1.metric("Model version", h["model_version"])
        hc1.metric("Data validation", "PASS ✅" if h["data_ok"] else "FAIL ❌")
        hc2.metric("Snapshot age (days)", h["freshness"].get("age_days", "—"))
        hc2.metric("Indexed records", f"{h['records']:,}")
        fb = h["feedback"]
        hc3.metric("Feedback events", fb["total_feedback"])
        hc3.metric("Skip rate", f"{fb['skip_rate']:.0%}" + (" ⚠️" if fb["drift_warning"] else ""))
        if fb["drift_warning"]:
            st.warning("Skip rate is high — ranking quality may be drifting. This is the "
                       "monitoring signal a production recommender needs (Lecture 10).")
        st.caption("Data validation runs schema, null, and range checks (Great-Expectations style). "
                   "Freshness + skip-rate are the drift signals the dashboard surfaces so failures "
                   "aren't silent.")
    except Exception:
        log.exception("health_panel_failed")
        st.caption("Health panel unavailable.")

