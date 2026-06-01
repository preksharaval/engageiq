"""
Test suite for EngageIQ. Run: pytest tests/ -v

These are the regression tests the CI workflow gates deploys on (Lecture 10:
"deploying without tests" is a production killer; nothing ships unless these pass).
"""
import sys, os
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))


# ── data layer ────────────────────────────────────────────────────────────
def test_dataset_meets_grading_floor():
    from monitoring import validate_dataset
    r = validate_dataset(strict=False)
    assert r["total_records"] >= 10_000, "need >=10k records for full data-pipeline credit"
    assert r["distinct_domains"] == 15, "all 15 brief domains must be present"
    assert {"github", "hackernews", "reddit"}.issubset(set(r["sources"]))
    assert r["passed"], f"data validation failures: {r['failures']}"


def test_no_corrupt_rows():
    from monitoring import validate_dataset
    r = validate_dataset()
    assert r["null_titles"] == 0
    assert r["effort_out_of_range"] == 0
    assert r["negative_scores"] == 0


# ── retrieval + ranking ─────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def ranker():
    from score.composite import Ranker
    return Ranker()


def test_ranking_returns_requested_n(ranker):
    res = ranker.rank(interests=["ml", "ai_research"], free_text="pytorch nlp",
                      platforms=["github", "hackernews", "reddit"], topn=10)
    assert len(res) == 10


def test_ranking_is_sorted_descending(ranker):
    res = ranker.rank(interests=["devops_k8s"], free_text="kubernetes",
                      platforms=["github"], topn=10)
    scores = [o["composite"] for o in res]
    assert scores == sorted(scores, reverse=True), "ranking must be ordered by score"


def test_why_components_present_and_bounded(ranker):
    res = ranker.rank(interests=["frontend_web"], free_text="react", topn=5)
    for o in res:
        c = o["components"]
        assert {"relevance", "community_health", "visibility_potential", "effort_inv"} <= set(c)
        assert 0.0 <= c["relevance"] <= 1.0001


def test_platform_filter_respected(ranker):
    res = ranker.rank(interests=["ml"], free_text="machine learning",
                      platforms=["github"], topn=15)
    assert all(o["source"] == "github" for o in res)


# ── dedup (streaming) ────────────────────────────────────────────────────────
def test_streaming_dedup_rejects_duplicates():
    from ingest.stream_pipeline import StreamProcessor
    proc = StreamProcessor()
    rec = {"id": "a1", "title": "Add retry logic to the kafka consumer",
           "body": "", "url": "http://x/1", "source": "github"}
    assert proc.process(rec) is True            # first time: novel
    assert proc.process(rec) is False           # exact url dup rejected
    # same content cross-posted to another platform (different url) -> near-dup
    crosspost = {"id": "a2", "title": "Add retry logic to the kafka consumer",
                 "body": "", "url": "http://x/2", "source": "reddit"}
    assert proc.process(crosspost) is False     # near-dup rejected by MinHash-LSH


# ── adaptive learning + cold start ──────────────────────────────────────────
def test_bandit_cold_start_low_trust():
    from learn.bandit import LinUCB
    m = LinUCB()
    assert m.is_cold
    assert m.trust() <= 0.2, "a brand-new user should barely trust the bandit"


def test_bandit_warms_up_with_feedback():
    from learn.bandit import LinUCB
    m = LinUCB()
    for _ in range(6):
        m.update(np.ones(7) * 0.5, 1.0)
    assert not m.is_cold
    assert m.trust() > 0.2


def test_bandit_persistence_roundtrip():
    from learn.bandit import LinUCB
    m = LinUCB()
    m.update(np.array([0.5, 0.5, 0.5, 0.5, 1, 0, 0], float), 2.0)
    blob = m.dumps()
    m2 = LinUCB.loads(blob)
    assert m2.n_updates == m.n_updates
    assert np.allclose(m2.A, m.A)


# ── personas (robustness) ────────────────────────────────────────────────────
def test_all_named_personas_pass():
    from eval.personas import run_personas
    results = run_personas(topn=10)
    failed = [name for name, ok, _ in results if not ok]
    assert not failed, f"these personas failed: {failed}"


# ── sketches (Lecture 2) ─────────────────────────────────────────────────────
def test_bloom_filter_no_false_negatives():
    from sketch import BloomFilter
    bf = BloomFilter(n=5000, fpp=0.01)
    items = [f"repo/{i}" for i in range(2000)]
    for it in items:
        bf.add(it)
    # a Bloom filter must never produce a false negative
    assert all(it in bf for it in items)


def test_count_min_never_undercounts():
    from sketch import CountMinSketch
    cms = CountMinSketch()
    truth = {"llm": 50, "rag": 30, "kafka": 5}
    for tok, c in truth.items():
        for _ in range(c):
            cms.update(tok)
    for tok, c in truth.items():
        assert cms.query(tok) >= c          # CMS guarantee: estimate >= true count


# ── diversity re-rank (Lecture 6) ────────────────────────────────────────────
def test_diversity_rerank_reduces_source_repetition(ranker):
    plain = ranker.rank(interests=["ml", "ai_research"], free_text="machine learning",
                        platforms=["github", "hackernews", "reddit"], topn=10, diversity=False)
    diverse = ranker.rank(interests=["ml", "ai_research"], free_text="machine learning",
                          platforms=["github", "hackernews", "reddit"], topn=10, diversity=True)
    # diversity should not produce a more lopsided top-10 than the plain ranking
    from collections import Counter
    top_src = lambda r: Counter(o["source"] for o in r[:10]).most_common(1)[0][1]
    assert top_src(diverse) <= top_src(plain) + 0  # at least as balanced


def test_no_hardcoded_secrets_in_repo():
    bad = []
    for p in (ROOT / "code").rglob("*.py"):
        text = p.read_text(errors="ignore")
        for marker in ("ghp_", "sk-ant-", "AKIA"):
            # allow the literal marker only inside obvious placeholders
            for line in text.splitlines():
                if marker in line and not any(tok in line for tok in
                                              ("environ", "getenv", "example", "placeholder", "PASTE", "require_env")):
                    bad.append(f"{p.name}: {line.strip()[:60]}")
    assert not bad, f"possible hardcoded secrets: {bad}"
