"""
reddit_ingest.py — Reddit posts via PRAW (read-only).

Set credentials (from https://www.reddit.com/prefs/apps):
  export REDDIT_CLIENT_ID=...   REDDIT_CLIENT_SECRET=...   REDDIT_USER_AGENT="engageiq by u/you"
Run:  python code/ingest/reddit_ingest.py --per-sub 120
Writes data/raw/reddit.jsonl.
"""
from __future__ import annotations
import sys, os, json, argparse, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, load_domains  # noqa: E402


def _client():
    import praw
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.getenv("REDDIT_USER_AGENT", "engageiq/0.1"),
    )


def main(per_sub: int):
    reddit = _client()
    cfg = load_domains()
    path = RAW / "reddit.jsonl"
    n = 0
    with open(path, "w") as f:
        for dkey, d in cfg["domains"].items():
            for sub in d["subreddits"]:
                try:
                    sr = reddit.subreddit(sub)
                    size = getattr(sr, "subscribers", 0) or 0
                    for post in sr.hot(limit=per_sub):
                        if post.stickied:
                            continue
                        rec = {
                            "source": "reddit", "domain": dkey,
                            "opp_type": "discussion" if post.num_comments > 25 else "post",
                            "title": post.title or "",
                            "body": (post.selftext or "")[:1000],
                            "url": f"https://reddit.com{post.permalink}",
                            "author": str(post.author) if post.author else None,
                            "created_at": dt.datetime.utcfromtimestamp(post.created_utc).isoformat(),
                            "score_raw": int(post.score), "num_comments": int(post.num_comments),
                            "community_size": int(size), "tags": [sub],
                        }
                        if rec["title"]:
                            f.write(json.dumps(rec) + "\n"); n += 1
                except Exception as e:
                    print(f"  ! r/{sub}: {e}")
    print(f"[reddit_ingest] wrote {n} records -> {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-sub", type=int, default=120)
    main(ap.parse_args().per_sub)
