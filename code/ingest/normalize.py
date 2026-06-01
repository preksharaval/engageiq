"""
normalize.py — merge data/raw/*.jsonl, near-dedup with MinHash LSH, load into SQLite.

MinHash LSH (datasketch) is BAX-423 technique #3 (counts toward data-pipeline quality):
catches near-duplicate posts (cross-posts, reworded titles) that exact-URL dedup misses.

Run after the ingestion scripts:  python code/ingest/normalize.py
Overwrites the opportunities table with REAL data (replacing the synthetic snapshot).
"""
from __future__ import annotations
import sys, json, glob, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, init_db, DB_PATH  # noqa: E402

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


def _velocity(created_at: str, score: int, comments: int) -> float:
    try:
        c = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if c.tzinfo is None:
            c = c.replace(tzinfo=dt.timezone.utc)
        age_h = max(1.0, (dt.datetime.now(dt.timezone.utc) - c).total_seconds() / 3600)
    except Exception:
        age_h = 24.0
    return round((score + comments) / age_h, 3)


def _effort(rec: dict) -> float:
    base = {"pr": 0.75, "issue": 0.35, "discussion": 0.25, "post": 0.2, "show": 0.5}
    return base.get(rec.get("opp_type", "post"), 0.4)


def normalize():
    files = glob.glob(str(RAW / "*.jsonl"))
    if not files:
        raise SystemExit("No raw files. Run the ingestion scripts first (or use make_snapshot.py).")

    lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    seen_urls = set()
    kept, n_in, n_url_dup, n_lsh_dup = [], 0, 0, 0

    for fp in files:
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_in += 1
                rec = json.loads(line)
                url = rec.get("url")
                if url and url in seen_urls:
                    n_url_dup += 1
                    continue
                text = (rec.get("title", "") + " " + rec.get("body", "")).strip()
                mh = _minhash(text)
                if lsh.query(mh):           # near-duplicate of something already kept
                    n_lsh_dup += 1
                    continue
                key = f"k{len(kept)}"
                lsh.insert(key, mh)
                if url:
                    seen_urls.add(url)
                kept.append(rec)

    # build rows
    import hashlib
    rows = []
    for i, rec in enumerate(kept):
        oid = f"{rec.get('source','x')}_{hashlib.md5((rec.get('url') or str(i)).encode()).hexdigest()[:12]}"
        score = int(rec.get("score_raw") or 0)
        comments = int(rec.get("num_comments") or 0)
        created = rec.get("created_at") or dt.datetime.now(dt.timezone.utc).isoformat()
        rows.append((
            oid, rec.get("source"), rec.get("domain"), rec.get("opp_type", "post"),
            rec.get("title", ""), rec.get("body", ""), rec.get("url"), rec.get("author"),
            created, score, comments, _velocity(created, score, comments),
            int(rec.get("community_size") or 0), _effort(rec),
            json.dumps(rec.get("tags", [])),
        ))

    conn = init_db()
    conn.execute("DELETE FROM opportunities")
    conn.executemany(
        """INSERT OR REPLACE INTO opportunities
           (id,source,domain,opp_type,title,body,url,author,created_at,
            score_raw,num_comments,velocity,community_size,effort,tags)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    conn.close()

    print(f"[normalize] in={n_in}  url_dups={n_url_dup}  lsh_dups={n_lsh_dup}  kept={total}")
    print(f"[normalize] loaded {total} records -> {DB_PATH}")
    print("[normalize] NEXT: rebuild the index ->  python code/embed/build_index.py")
    return {"in": n_in, "url_dups": n_url_dup, "lsh_dups": n_lsh_dup, "kept": total}


if __name__ == "__main__":
    normalize()
