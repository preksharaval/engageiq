"""
make_snapshot.py — Build a realistic OFFLINE SNAPSHOT so the app runs end-to-end
without network access to GitHub/Reddit/HN.

  ⚠️  THIS IS SYNTHETIC DATA, clearly labelled (author names start with 'synth_').
      For your graded submission, run the REAL ingestion in code/ingest/ with your
      API credentials, then normalize.py to overwrite this snapshot with genuine
      records. The schema is identical, so nothing downstream changes.

Produces >= 10,000 deduped records spanning all 15 domains and writes them into
opportunities in data/engageiq.sqlite.
"""
from __future__ import annotations
import json, random, hashlib, datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import init_db, load_domains, DB_PATH  # noqa: E402

random.seed(423)

SOURCES = ["github", "reddit", "hackernews"]
OPP_BY_SOURCE = {
    "github": ["issue", "pr", "discussion"],
    "reddit": ["post", "discussion"],
    "hackernews": ["post", "show"],
}

# Title templates per opp_type. {kw} = a domain keyword, {tech} = a second keyword.
TITLE_TEMPLATES = {
    "issue": [
        "good first issue: improve {kw} error messages",
        "{kw}: flaky test on CI when {tech} enabled",
        "help wanted: document the {kw} configuration surface",
        "regression in {kw} after the {tech} refactor",
        "RFC: should {kw} support {tech} natively?",
        "memory leak in {kw} under high {tech} load",
    ],
    "pr": [
        "feat: add {tech} support to {kw}",
        "perf: 2x faster {kw} by reusing {tech} buffers",
        "docs: rewrite the {kw} getting-started guide",
        "fix: handle empty {tech} input in {kw}",
        "refactor: split {kw} module for {tech}",
    ],
    "discussion": [
        "How are people handling {kw} at scale with {tech}?",
        "Show & tell: my {kw} setup using {tech}",
        "Best practices for {kw} testing in 2026",
        "Migrating from legacy {tech} to {kw} — lessons learned",
    ],
    "post": [
        "Why we moved our {kw} stack to {tech}",
        "A practical guide to {kw} for {tech} teams",
        "{kw} in production: what nobody tells you about {tech}",
        "Ask: is {kw} still worth learning given {tech}?",
        "The hidden cost of {kw} when you add {tech}",
    ],
    "show": [
        "Show HN: an open-source {kw} tool built on {tech}",
        "Show HN: I made {kw} 10x simpler with {tech}",
        "Show HN: {kw} dashboard with live {tech} metrics",
    ],
}

BODY_SNIPPETS = [
    "We've been running this in production for a few months and wanted to share what broke.",
    "Looking for contributors who understand {tech}; the change is well scoped and tested.",
    "Benchmarks attached. The bottleneck turned out to be {kw}, not {tech} as we assumed.",
    "Open question to the community: how do you keep {kw} maintainable as the team grows?",
    "Wrote up the design doc; feedback on the {tech} tradeoffs especially welcome.",
    "This is beginner-friendly. If you've touched {kw} before, the fix is about an hour.",
    "Migration notes inside. The {tech} path saved us roughly 30% on infra.",
]


def _mk_id(source: str, n: int) -> str:
    return f"{source}_{hashlib.md5(f'{source}{n}'.encode()).hexdigest()[:12]}"


def _engagement_profile(source: str, opp_type: str):
    """Return (score_raw, num_comments, community_size, effort) with source-realistic ranges."""
    if source == "github":
        community = random.choice([random.randint(50, 800), random.randint(800, 40000)])
        score = max(0, int(random.gauss(community * 0.02, community * 0.02)))
        comments = random.randint(0, 40)
        effort = {"issue": 0.35, "pr": 0.75, "discussion": 0.25}[opp_type]
    elif source == "reddit":
        community = random.randint(8000, 600000)
        score = max(0, int(abs(random.gauss(120, 250))))
        comments = random.randint(0, 220)
        effort = 0.2
    else:  # hackernews
        community = random.randint(20000, 500000)
        score = max(0, int(abs(random.gauss(80, 160))))
        comments = random.randint(0, 300)
        effort = 0.3 if opp_type == "post" else 0.6
    effort = min(1.0, max(0.05, effort + random.uniform(-0.1, 0.1)))
    return score, comments, community, round(effort, 3)


def generate(target: int = 11000) -> int:
    cfg = load_domains()
    domains = cfg["domains"]
    dom_keys = list(domains.keys())
    now = dt.datetime.now(dt.timezone.utc)

    rows = []
    per_domain = target // len(dom_keys) + 1
    n = 0
    for dkey in dom_keys:
        kws = domains[dkey]["keywords"]
        for _ in range(per_domain):
            source = random.choices(SOURCES, weights=[0.45, 0.3, 0.25])[0]
            opp_type = random.choice(OPP_BY_SOURCE[source])
            kw, tech = random.sample(kws, 2) if len(kws) >= 2 else (kws[0], kws[0])
            title = random.choice(TITLE_TEMPLATES[opp_type]).format(kw=kw, tech=tech)
            body = " ".join(random.sample(BODY_SNIPPETS, k=random.randint(1, 3))).format(kw=kw, tech=tech)
            score, comments, community, effort = _engagement_profile(source, opp_type)
            age_hours = random.uniform(1, 72)
            created = now - dt.timedelta(hours=age_hours)
            velocity = round((score + comments) / age_hours, 3)
            rows.append((
                _mk_id(source, n), source, dkey, opp_type, title, body,
                f"https://example.{source}.test/{dkey}/{n}", f"synth_user_{n % 900}",
                created.isoformat(), score, comments, velocity, community, effort,
                json.dumps([kw, tech]),
            ))
            n += 1

    random.shuffle(rows)
    rows = rows[:target]

    conn = init_db()
    conn.execute("DELETE FROM opportunities")
    conn.executemany(
        """INSERT OR REPLACE INTO opportunities
           (id,source,domain,opp_type,title,body,url,author,created_at,
            score_raw,num_comments,velocity,community_size,effort,tags)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    cnt = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    conn.close()
    return cnt


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=11000)
    args = ap.parse_args()
    total = generate(args.target)
    print(f"[make_snapshot] wrote {total} synthetic opportunities to {DB_PATH}")
