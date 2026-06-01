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
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
  --bg:        #080b14;
  --surface:   #0e1424;
  --glass:     rgba(255,255,255,0.04);
  --glass-b:   rgba(255,255,255,0.10);
  --accent:    #00e5ff;
  --accent2:   #7c3aed;
  --accent3:   #f59e0b;
  --text:      #e2e8f0;
  --muted:     #64748b;
  --success:   #10b981;
  --danger:    #ef4444;
  --grad:      linear-gradient(135deg,#00e5ff22,#7c3aed22);
}

html, body, [data-testid="stApp"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Syne', sans-serif;
}

/* ── sidebar ── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0a0f1e 0%, #0e1628 100%) !important;
  border-right: 1px solid rgba(0,229,255,0.12) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── header ── */
.eq-header {
  text-align: center;
  padding: 2.5rem 1rem 1.5rem;
  position: relative;
}
.eq-header h1 {
  font-family: 'Syne', sans-serif;
  font-size: 3.2rem;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(90deg, #00e5ff, #7c3aed, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  line-height: 1;
}
.eq-header p {
  color: var(--muted);
  font-family: 'Space Mono', monospace;
  font-size: 0.78rem;
  margin-top: 0.5rem;
  letter-spacing: 2px;
  text-transform: uppercase;
}

/* ── glass card ── */
.eq-card {
  background: var(--glass);
  border: 1px solid var(--glass-b);
  border-radius: 16px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1rem;
  backdrop-filter: blur(20px);
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}
.eq-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.5;
}
.eq-card:hover {
  border-color: rgba(0,229,255,0.30);
  background: rgba(255,255,255,0.06);
  transform: translateY(-1px);
  box-shadow: 0 8px 32px rgba(0,229,255,0.08);
}

/* ── rank badge ── */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px; height: 32px;
  border-radius: 50%;
  font-family: 'Space Mono', monospace;
  font-weight: 700;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.rank-1 { background: linear-gradient(135deg,#f59e0b,#ef4444); color:#000; }
.rank-2 { background: linear-gradient(135deg,#94a3b8,#cbd5e1); color:#000; }
.rank-3 { background: linear-gradient(135deg,#b45309,#d97706); color:#000; }
.rank-n { background: rgba(255,255,255,0.08); color: var(--muted); }

/* ── score arc ── */
.score-ring {
  display: flex; flex-direction: column; align-items: center;
  gap: 2px;
}
.score-val {
  font-family: 'Space Mono', monospace;
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.score-lbl { font-size: 0.62rem; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }

/* ── source chip ── */
.chip {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-family: 'Space Mono', monospace;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.chip-github    { background: rgba(139,92,246,0.20); color:#a78bfa; border:1px solid #7c3aed44; }
.chip-hackernews{ background: rgba(245,158,11,0.20); color:#fbbf24; border:1px solid #f59e0b44; }
.chip-reddit    { background: rgba(239,68,68,0.20);  color:#f87171; border:1px solid #ef444444; }

/* ── domain tag ── */
.domain-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.65rem;
  background: rgba(0,229,255,0.08);
  color: var(--accent);
  border: 1px solid rgba(0,229,255,0.20);
  font-family: 'Space Mono', monospace;
}

/* ── action button row ── */
.action-row { display: flex; gap: 8px; margin-top: 0.75rem; }

/* ── why panel ── */
.why-bar-wrap { margin: 0.5rem 0; }
.why-label { font-size: 0.72rem; color: var(--muted); margin-bottom: 2px; font-family: 'Space Mono', monospace; }
.why-bar-bg { background: rgba(255,255,255,0.06); border-radius: 4px; height: 8px; overflow: hidden; }
.why-bar-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }

/* ── metric pill ── */
.metric-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  font-size: 0.72rem;
  font-family: 'Space Mono', monospace;
}

/* ── tab styling ── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,0.03);
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
  border: 1px solid rgba(255,255,255,0.08);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 8px !important;
  color: var(--muted) !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg,rgba(0,229,255,0.15),rgba(124,58,237,0.15)) !important;
  color: var(--accent) !important;
  border: 1px solid rgba(0,229,255,0.25) !important;
}

/* ── inputs ── */
.stSelectbox > div, .stMultiSelect > div, .stSlider, .stTextArea textarea {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
}
.stTextArea textarea { background: rgba(255,255,255,0.03) !important; color: var(--text) !important; }

/* ── buttons ── */
.stButton button {
  background: linear-gradient(135deg,rgba(0,229,255,0.10),rgba(124,58,237,0.10)) !important;
  border: 1px solid rgba(0,229,255,0.25) !important;
  color: var(--accent) !important;
  border-radius: 8px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 0.75rem !important;
  transition: all 0.2s !important;
}
.stButton button:hover {
  background: linear-gradient(135deg,rgba(0,229,255,0.20),rgba(124,58,237,0.20)) !important;
  border-color: var(--accent) !important;
  transform: translateY(-1px) !important;
}

/* ── misc ── */
.stMarkdown h3 { font-family: 'Syne', sans-serif; font-size: 1rem; color: var(--accent); }
hr { border-color: rgba(255,255,255,0.06) !important; }
.stSpinner { color: var(--accent) !important; }
[data-testid="stMetric"] { background: var(--glass); border-radius: 12px; padding: 0.75rem; border: 1px solid var(--glass-b); }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: 'Space Mono', monospace !important; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.72rem !important; }

/* ── 3D float animation ── */
@keyframes float3d {
  0%,100% { transform: translateY(0px) rotateX(0deg); }
  50%      { transform: translateY(-4px) rotateX(1deg); }
}
.float-anim { animation: float3d 4s ease-in-out infinite; }

/* ── glow orbs ── */
.orb {
  position: fixed; border-radius: 50%; filter: blur(80px);
  pointer-events: none; z-index: 0; opacity: 0.15;
}
.orb1 { width:400px;height:400px; background:#00e5ff; top:-100px; right:-100px; }
.orb2 { width:300px;height:300px; background:#7c3aed; bottom:-80px; left:-80px; }
</style>

<div class="orb orb1"></div>
<div class="orb orb2"></div>
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
    "relevance":          "#00e5ff",
    "community_health":   "#7c3aed",
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
          <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;
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
            st.markdown(f"""<div style="background:rgba(0,229,255,0.05);border-left:2px solid var(--accent);
                            border-radius:8px;padding:10px 14px;font-size:0.82rem;line-height:1.5;
                            color:#cbd5e1;">{action}</div>""", unsafe_allow_html=True)
            st.markdown(f"[🔗 View on {src}]({opp.get('url','#')})")
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
      <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;
                  background:linear-gradient(90deg,#00e5ff,#7c3aed);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;">⚡ EngageIQ</div>
      <div style="font-family:'Space Mono',monospace;font-size:0.65rem;
                  color:#64748b;letter-spacing:2px;text-transform:uppercase;">
        opportunity scorer
      </div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    user_id = st.text_input("Your ID", value="preksha", placeholder="any username")
    st.session_state["user_id"] = user_id

    interests = st.multiselect(
        "Domains", options=list(DOMAIN_LABELS.keys()),
        format_func=lambda k: DOMAIN_LABELS[k],
        default=["ml", "ai_research", "developer_tools"],
    )
    free_text = st.text_area("Describe your goals", placeholder="e.g. I want to contribute to ML projects and build my GitHub portfolio...", height=90)
    time_budget = st.slider("⏱ Hours/week", 1, 20, 5)
    platforms = st.multiselect("Platforms", ["github","hackernews","reddit"],
                               default=["github","hackernews","reddit"])
    topn = st.slider("Results to show", 5, 30, 10)
    adaptive = st.toggle("🧠 Adaptive bandit ranking", value=True)
    diversify = st.toggle("🎨 Diversity re-ranking", value=True,
                          help="Stage-3 re-rank: penalize repeated source+domain so the "
                               "list isn't ten near-identical items (Lecture 6).")

    st.divider()
    st.markdown("<div style='font-size:0.7rem;color:#64748b;font-family:Space Mono,monospace;'>BAX-423 · Spring 2026<br>UC Davis GSM</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""<div class="eq-header">
  <h1>EngageIQ</h1>
  <p>Smart Engagement Opportunity Scorer · GitHub · Hacker News · Reddit</p>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["⚡ Discover", "📈 Trends", "📄 Brief", "🔬 Methods"])

# ── TAB 1: DISCOVER ──────────────────────────────────────────────────────────
with tab1:
    if not interests:
        st.markdown("""<div class="eq-card" style="text-align:center;padding:2rem;">
          <div style="font-size:2rem;">👈</div>
          <div style="color:var(--muted);font-family:'Space Mono',monospace;font-size:0.8rem;margin-top:0.5rem;">
            Pick your domains in the sidebar to discover opportunities
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
                        colorscale=[[0,"#7c3aed"],[0.5,"#00e5ff"],[1,"#f59e0b"]],
                        opacity=0.85,
                        line=dict(width=1, color="rgba(255,255,255,0.3)"),
                    ),
                    textfont=dict(color="white", size=9),
                )])
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0,r=0,t=30,b=0), height=300,
                    font=dict(color="#94a3b8", family="Space Mono"),
                    scene=dict(
                        bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(title="Relevance", color="#64748b", gridcolor="#1e293b"),
                        yaxis=dict(title="Community", color="#64748b", gridcolor="#1e293b"),
                        zaxis=dict(title="Visibility", color="#64748b", gridcolor="#1e293b"),
                    ),
                    title=dict(text="3D opportunity space", font=dict(color="#00e5ff", size=12, family="Space Mono"), x=0.5),
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
                        color_continuous_scale=[[0,"#7c3aed"],[1,"#00e5ff"]],
                        labels={"estimated_freq":"Count-Min estimate","keyword":""})
        fig_kw.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(8,11,20,0.8)",
            font=dict(color="#94a3b8", family="Space Mono"),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
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
                             color_discrete_sequence=["#7c3aed","#f59e0b","#ef4444"])
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color="#94a3b8"), margin=dict(l=0,r=0,t=20,b=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 📊 Volume Over Time")
    vol = T.volume_over_time(window_hours=72)
    if not vol.empty:
        fig_vol = px.area(vol, x="hour", y="count",
                          color_discrete_sequence=["#00e5ff"])
        fig_vol.update_traces(fill="tozeroy", fillcolor="rgba(0,229,255,0.08)", line=dict(color="#00e5ff", width=2))
        fig_vol.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(8,11,20,0.8)",
            font=dict(color="#94a3b8", family="Space Mono"),
            xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
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
                <span style="font-family:'Space Mono',monospace;color:var(--muted);font-size:0.8rem;">#{i+1}</span>
                <span class="chip {chip_cls}">{src_icon} {opp['source']}</span>
                <span style="flex:1;font-size:0.88rem;color:#e2e8f0;">{opp['title'][:90]}</span>
                <span style="font-family:'Space Mono',monospace;color:var(--accent);font-weight:700;">{score:.3f}</span>
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

    fig_dom = px.bar(domain_df, x="domain", y="count",
                     color="count", color_continuous_scale=[[0,"#7c3aed"],[1,"#00e5ff"]])
    fig_dom.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(8,11,20,0.8)",
                           font=dict(color="#94a3b8",family="Space Mono"),
                           xaxis=dict(tickangle=-35,gridcolor="#1e293b"),
                           yaxis=dict(gridcolor="#1e293b"), coloraxis_showscale=False,
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

