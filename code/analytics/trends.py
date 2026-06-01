"""
trends.py — trend analytics over the snapshot.

  trending_topics:   highest-velocity opportunities in a rolling window
  growing_domains:   domain volume + mean velocity (fastest-moving areas)
  source_mix:        record counts by source
  volume_over_time:  records bucketed by hour of creation (last 72h)

All return pandas DataFrames so the Streamlit app can hand them to Plotly directly.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import connect  # noqa: E402


def _df() -> pd.DataFrame:
    conn = connect()
    df = pd.read_sql_query("SELECT * FROM opportunities", conn)
    conn.close()
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df


def trending_topics(domains=None, window_hours=24, top=15) -> pd.DataFrame:
    df = _df()
    if domains:
        df = df[df["domain"].isin(domains)]
    cutoff = df["created_at"].max() - pd.Timedelta(hours=window_hours)
    recent = df[df["created_at"] >= cutoff].copy()
    if recent.empty:
        recent = df.copy()
    recent = recent.sort_values("velocity", ascending=False)
    return recent[["title", "domain", "source", "velocity", "score_raw",
                   "num_comments", "url"]].head(top).reset_index(drop=True)


def trending_keywords(top=12) -> pd.DataFrame:
    """Top trending keywords via a Count-Min Sketch (BAX-423 Lecture 2 sketching).

    We stream every opportunity title through a CMS instead of holding a full
    {term: count} dict — O(1) memory regardless of vocabulary size. Velocity-
    weighted so fast-moving posts count for more (Lina's 'rising' criterion)."""
    import re
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from sketch import CountMinSketch

    STOP = {"the","a","an","to","for","of","and","in","on","with","add","fix",
            "is","how","i","my","using","use","new","this","from","via","your"}
    df = _df()
    cms = CountMinSketch(epsilon=0.001, delta=0.01)
    vocab = set()
    for title, vel in zip(df["title"].fillna(""), df["velocity"].fillna(0)):
        weight = 1 + int(min(5, vel))         # velocity-weighted frequency
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{2,}", str(title).lower()):
            if tok in STOP:
                continue
            cms.update(tok, weight)
            vocab.add(tok)
    rows = [{"keyword": t, "estimated_freq": cms.query(t)} for t in vocab]
    out = pd.DataFrame(rows).sort_values("estimated_freq", ascending=False).head(top)
    return out.reset_index(drop=True)



    df = _df()
    g = df.groupby("domain").agg(
        volume=("id", "count"),
        mean_velocity=("velocity", "mean"),
        median_comments=("num_comments", "median"),
    ).reset_index().sort_values("mean_velocity", ascending=False)
    g["mean_velocity"] = g["mean_velocity"].round(2)
    return g.reset_index(drop=True)


def source_mix() -> pd.DataFrame:
    df = _df()
    return df.groupby("source").size().reset_index(name="count")


def volume_over_time(window_hours=72) -> pd.DataFrame:
    df = _df()
    cutoff = df["created_at"].max() - pd.Timedelta(hours=window_hours)
    recent = df[df["created_at"] >= cutoff].copy()
    recent["hour"] = recent["created_at"].dt.floor("h")
    out = recent.groupby(["hour", "source"]).size().reset_index(name="count")
    return out


if __name__ == "__main__":
    print("== trending ==");  print(trending_topics().head(5).to_string())
    print("\n== growing domains =="); print(growing_domains().to_string())
    print("\n== source mix =="); print(source_mix().to_string())
