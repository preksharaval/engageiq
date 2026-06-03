"""
brief.py — export a personalized weekly engagement brief (PDF) and CSV.

build_brief_pdf(profile, ranked) -> bytes      (used by the app's download button)
build_csv(ranked) -> str
"""
from __future__ import annotations
import sys, io, csv, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm.suggest_action import suggest_action, backend_name  # noqa: E402
from analytics.trends import trending_topics  # noqa: E402

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, ListFlowable, ListItem)


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H", parent=ss["Heading1"], textColor=colors.HexColor("#1d4ed8"), fontSize=18))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], textColor=colors.HexColor("#475569"), fontSize=9))
    ss.add(ParagraphStyle("Act", parent=ss["Normal"], fontSize=9, leftIndent=10,
                          textColor=colors.HexColor("#0f172a")))
    return ss


def build_brief_pdf(profile: dict, ranked: list[dict], top: int = 10) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.6 * inch)
    ss = _styles()
    story = []

    story.append(Paragraph("EngageIQ — Weekly Engagement Brief", ss["H"]))
    today = dt.date.today().strftime("%B %d, %Y")
    interests = ", ".join(profile.get("interests", [])) or "—"
    story.append(Paragraph(
        f"Generated {today} &nbsp;·&nbsp; Focus: {interests} &nbsp;·&nbsp; "
        f"Time budget: {profile.get('time_budget', 5)} hrs/week &nbsp;·&nbsp; "
        f"Suggested-action engine: {backend_name()}", ss["Sub"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Your top {top} opportunities this week", ss["Heading2"]))
    items = []
    budget = float(profile.get("time_budget", 5))
    spent = 0.0
    for i, o in enumerate(ranked[:top], 1):
        est = round(0.3 + o["effort"] * 1.2, 1)  # rough hrs estimate
        spent += est
        head = (f"<b>{i}. [{o['domain']}/{o['source']}]</b> {o['title']}<br/>"
                f"<font size=8 color='#64748b'>score {o['composite']:.3f} · "
                f"{o['score_raw']} pts · {o['num_comments']} comments · ~{est}h</font>")
        action = suggest_action(o)
        items.append(ListItem(
            [Paragraph(head, ss["Normal"]),
             Paragraph(f"<b>Suggested action:</b> {action}", ss["Act"]),
             Spacer(1, 5)], value=i))
    story.append(ListFlowable(items, bulletType="1", leftIndent=12))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"<font size=9 color='#475569'>Estimated time for these 10: ~{spent:.1f}h "
        f"(budget {budget}h). Prioritize the top {max(1, int(budget // 1))} if short on time.</font>",
        ss["Normal"]))
    story.append(Spacer(1, 14))

    # ── data sources disclosure (honest about what's real vs synthetic) ──
    story.append(Paragraph(
        "<font size=8 color='#64748b'><b>Data sources:</b> 865 records are real GitHub API pulls "
        "(including good-first-issue repos and issues). The rest are realistic synthetic records "
        "for Hacker News and Reddit, generated because those APIs were network-restricted in the "
        "build environment. Ingestion scripts ship with the project and pull live HN/Reddit data "
        "with API credentials. See <i>Limitations</i> in the project brief.</font>", ss["Normal"]))
    story.append(Spacer(1, 12))

    # trends snapshot
    story.append(Paragraph("Trending in your domains", ss["Heading2"]))
    tr = trending_topics(domains=profile.get("interests") or None, top=5)
    data = [["Topic", "Domain", "Velocity"]]
    for _, r in tr.iterrows():
        data.append([r["title"][:60], r["domain"], f"{r['velocity']:.1f}"])
    t = Table(data, colWidths=[3.6 * inch, 1.3 * inch, 0.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ]))
    story.append(t)

    doc.build(story)
    return buf.getvalue()


def build_csv(ranked: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "domain", "source", "opp_type", "title", "composite",
                "score_raw", "num_comments", "velocity", "url", "suggested_action"])
    for i, o in enumerate(ranked, 1):
        w.writerow([i, o["domain"], o["source"], o["opp_type"], o["title"],
                    round(o["composite"], 4), o["score_raw"], o["num_comments"],
                    o["velocity"], o["url"], suggest_action(o)])
    return buf.getvalue()
