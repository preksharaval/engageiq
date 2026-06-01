"""
monitoring.py — data validation + runtime monitoring for EngageIQ.

Maps to two layers of the MLOps stack covered in Lecture 10:
  • Data layer    — schema / null / range checks before data is trusted
                    (the "Great Expectations" idea, kept dependency-free here).
  • Monitoring    — dataset freshness, feedback-distribution drift, and a
                    health check the dashboard surfaces.

Why this exists: EngageIQ is a recommender, and the lecture's Job-Rec case study
showed recommenders fail silently in production (stale data, drift, cold-start).
These checks make those failure modes visible instead of silent.
"""
from __future__ import annotations
import sys, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import connect, get_logger, MODEL_VERSION

log = get_logger("engageiq.monitor")

# Expectations the offline dataset must satisfy to be trusted for grading.
MIN_RECORDS = 10_000
MIN_DOMAINS = 15
REQUIRED_SOURCES = {"github", "hackernews", "reddit"}


class DataValidationError(Exception):
    pass


def validate_dataset(strict: bool = False) -> dict:
    """Run schema + content expectations over the opportunities table.
    Returns a report dict; raises DataValidationError in strict mode on failure."""
    conn = connect()
    report, failures = {}, []

    total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    report["total_records"] = total
    if total < MIN_RECORDS:
        failures.append(f"only {total} records (< {MIN_RECORDS})")

    ndomains = conn.execute("SELECT COUNT(DISTINCT domain) FROM opportunities").fetchone()[0]
    report["distinct_domains"] = ndomains
    if ndomains < MIN_DOMAINS:
        failures.append(f"only {ndomains} domains (< {MIN_DOMAINS})")

    sources = {r[0] for r in conn.execute("SELECT DISTINCT source FROM opportunities")}
    report["sources"] = sorted(sources)
    if not REQUIRED_SOURCES.issubset(sources):
        failures.append(f"missing sources: {REQUIRED_SOURCES - sources}")

    # null / empty critical fields
    null_titles = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE title IS NULL OR title=''").fetchone()[0]
    report["null_titles"] = null_titles
    if null_titles:
        failures.append(f"{null_titles} rows with empty title")

    null_urls = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE url IS NULL OR url=''").fetchone()[0]
    report["null_urls"] = null_urls

    # range checks: effort in [0,1], scores non-negative
    bad_effort = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE effort < 0 OR effort > 1").fetchone()[0]
    report["effort_out_of_range"] = bad_effort
    if bad_effort:
        failures.append(f"{bad_effort} rows with effort outside [0,1]")

    neg_scores = conn.execute(
        "SELECT COUNT(*) FROM opportunities WHERE score_raw < 0").fetchone()[0]
    report["negative_scores"] = neg_scores
    if neg_scores:
        failures.append(f"{neg_scores} rows with negative score")

    conn.close()
    report["passed"] = not failures
    report["failures"] = failures
    if failures:
        log.warning("data validation FAILED: %s", "; ".join(failures))
        if strict:
            raise DataValidationError("; ".join(failures))
    else:
        log.info("data validation passed (%d records, %d domains)", total, ndomains)
    return report


def freshness() -> dict:
    """How stale is the snapshot? The lecture flagged stale data as a silent killer."""
    conn = connect()
    row = conn.execute("SELECT MAX(created_at) FROM opportunities").fetchone()
    conn.close()
    latest = row[0] if row else None
    age_days = None
    if latest:
        try:
            t = dt.datetime.fromisoformat(latest.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=dt.timezone.utc)
            age_days = (dt.datetime.now(dt.timezone.utc) - t).days
        except Exception:
            pass
    return {"latest_record": latest, "age_days": age_days}


def feedback_drift() -> dict:
    """Watch the engage/bookmark/skip mix. A sudden skip spike is the signal that
    recommendation quality is drifting — define drift precisely, per the lecture."""
    conn = connect()
    rows = conn.execute(
        "SELECT action, COUNT(*) FROM feedback GROUP BY action").fetchall()
    conn.close()
    counts = {a: c for a, c in rows}
    total = sum(counts.values())
    skip_rate = counts.get("skip", 0) / total if total else 0.0
    # heuristic threshold: >60% skips means the ranker is serving poor items
    drifting = total >= 10 and skip_rate > 0.60
    return {"total_feedback": total, "counts": counts,
            "skip_rate": round(skip_rate, 3), "drift_warning": drifting}


def health() -> dict:
    """One-call health summary for the dashboard footer / a /health style check."""
    files = ["engageiq.sqlite", "embeddings.npy", "faiss.index"]
    from common import DATA
    present = {f: (DATA / f).exists() for f in files}
    val = validate_dataset(strict=False)
    return {
        "model_version": MODEL_VERSION,
        "artifacts_present": present,
        "data_ok": val["passed"],
        "records": val["total_records"],
        "freshness": freshness(),
        "feedback": feedback_drift(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(health(), indent=2, default=str))
