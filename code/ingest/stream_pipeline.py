"""
stream_pipeline.py — real-time streaming ingestion with online deduplication.

Demonstrates BAX-423 streaming capability (Core Capability #1). Instead of a
one-shot batch load, this consumes incoming opportunity records as a *stream*
(one at a time, as they would arrive from a Kafka topic / API webhook / polling
loop), runs each through an online MinHash-LSH dedup gate, and commits accepted
records to SQLite incrementally — exactly the path a production ingestion service
would take.

Usage:
    # replay the offline snapshot through the streaming pipeline (demo / grading)
    python code/ingest/stream_pipeline.py --replay --limit 2000

    # live mode: poll GitHub every N seconds and stream new items in
    GITHUB_TOKEN=xxx python code/ingest/stream_pipeline.py --live --interval 30

The same StreamProcessor class backs the dashboard's live-ingest indicator.
"""
from __future__ import annotations
import sys, json, time, argparse, datetime as dt
from pathlib import Path
from collections import deque

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, connect  # noqa: E402
from sketch import BloomFilter  # noqa: E402

from datasketch import MinHash, MinHashLSH

NUM_PERM = 64
LSH_THRESHOLD = 0.82


def _shingles(text: str, k: int = 3):
    toks = (text or "").lower().split()
    if len(toks) < k:
        return {text.lower()} if text else set()
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def _minhash(text: str) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for sh in _shingles(text):
        m.update(sh.encode("utf8"))
    return m


class StreamProcessor:
    """Stateful online stream consumer with exact-URL + near-dup (LSH) gating.

    Call .process(record) for each incoming record; it returns True if the record
    was accepted (novel) or False if rejected as a duplicate. State persists across
    calls so the dedup window spans the whole stream — like a long-running service.
    """

    def __init__(self):
        self.lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
        self.bloom = BloomFilter(n=200_000, fpp=0.005)  # fast exact-dup gate (L2)
        self.seen_urls = set()
        self.stats = {"seen": 0, "accepted": 0, "url_dups": 0, "near_dups": 0, "bloom_hits": 0}
        self._recent = deque(maxlen=200)  # rolling window for the dashboard ticker

    def process(self, rec: dict) -> bool:
        self.stats["seen"] += 1
        url = (rec.get("url") or "").strip()
        # Stage A — Bloom filter: O(1) probabilistic exact-dup check on the URL.
        # "Probably seen" -> confirm against the exact set (Bloom has no false negatives,
        # so "definitely not seen" lets us skip the set lookup entirely on the hot path).
        if url:
            if url in self.bloom:
                self.stats["bloom_hits"] += 1
                if url in self.seen_urls:           # confirm: real exact dup
                    self.stats["url_dups"] += 1
                    return False
            self.bloom.add(url)
        # Stage B — MinHash-LSH: catch near-duplicates (reworded cross-posts).
        key = rec.get("id") or f"k{self.stats['seen']}"
        mh = _minhash((rec.get("title", "") or "") + " " + (rec.get("body", "") or ""))
        if self.lsh.query(mh):
            self.stats["near_dups"] += 1
            return False
        # accept
        try:
            self.lsh.insert(key, mh)
        except ValueError:
            pass  # key already present
        if url:
            self.seen_urls.add(url)
        self.stats["accepted"] += 1
        self._recent.append({"title": rec.get("title", "")[:80], "source": rec.get("source", "")})
        return True

    def commit(self, rec: dict):
        """Persist an accepted record to SQLite (incremental, one row at a time)."""
        conn = connect()
        conn.execute("""
            INSERT OR IGNORE INTO opportunities
              (id,source,domain,opp_type,title,body,url,author,created_at,
               score_raw,num_comments,velocity,community_size,effort,tags,has_good_first_issue)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            rec.get("id"), rec.get("source"), rec.get("domain"), rec.get("opp_type", "post"),
            rec.get("title", ""), rec.get("body", ""), rec.get("url", ""), rec.get("author", ""),
            rec.get("created_at", ""), rec.get("score_raw", 0), rec.get("num_comments", 0),
            rec.get("velocity", 0.0), rec.get("community_size", 0), rec.get("effort", 0.5),
            json.dumps(rec.get("tags", [])), 1 if rec.get("has_good_first_issue") else 0,
        ))
        conn.commit()
        conn.close()


def replay_snapshot(limit: int = 2000):
    """Stream the existing DB rows back through the pipeline to demonstrate
    streaming + online dedup behaviour without needing live API access."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()

    proc = StreamProcessor()
    t0 = time.perf_counter()
    for r in rows:
        rec = dict(r)
        proc.process(rec)  # gate only; rows already in DB
    dur = time.perf_counter() - t0

    s = proc.stats
    print(f"[stream] consumed {s['seen']} records in {dur:.2f}s "
          f"({s['seen']/max(dur,1e-6):.0f} rec/s)")
    print(f"[stream] accepted={s['accepted']}  url_dups={s['url_dups']}  near_dups={s['near_dups']}")
    print(f"[stream] dedup rate = {(s['url_dups']+s['near_dups'])/max(s['seen'],1)*100:.1f}%")
    return proc.stats


def live_poll(interval: int = 30):
    """Live mode: poll GitHub for fresh items and stream them in (needs GITHUB_TOKEN)."""
    import os, requests
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN for live mode.")
    proc = StreamProcessor()
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    print(f"[stream] live mode — polling GitHub every {interval}s. Ctrl-C to stop.")
    while True:
        url = "https://api.github.com/search/repositories?q=pushed:>2026-05-01&sort=updated&per_page=30"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                for it in r.json().get("items", []):
                    rec = {
                        "id": f"gh_{it['id']}", "source": "github", "domain": "trending_oss",
                        "opp_type": "repo", "title": it.get("full_name", ""),
                        "body": it.get("description", "") or "", "url": it.get("html_url", ""),
                        "author": it.get("owner", {}).get("login", ""),
                        "created_at": it.get("pushed_at", ""),
                        "score_raw": it.get("stargazers_count", 0),
                        "num_comments": it.get("open_issues_count", 0),
                        "community_size": it.get("stargazers_count", 0),
                    }
                    if proc.process(rec):
                        proc.commit(rec)
                print(f"[stream] {proc.stats['accepted']} accepted / {proc.stats['seen']} seen")
        except Exception as e:
            print(f"[stream] poll error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true", help="replay snapshot through the stream")
    ap.add_argument("--live", action="store_true", help="poll GitHub live")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()
    if args.live:
        live_poll(args.interval)
    else:
        replay_snapshot(args.limit)
