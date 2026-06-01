"""Shared paths, schema, and helpers for EngageIQ."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path

# code/ -> repo root
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
DB_PATH = DATA / "engageiq.sqlite"
EMB_PATH = DATA / "embeddings.npy"
IDS_PATH = DATA / "embedding_ids.npy"
FAISS_PATH = DATA / "faiss.index"
DOMAINS_YAML = ROOT / "code" / "domains.yaml"

DATA.mkdir(exist_ok=True, parents=True)
RAW.mkdir(exist_ok=True, parents=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,          -- github | reddit | hackernews
    domain          TEXT NOT NULL,          -- one of the 15 domain keys
    opp_type        TEXT,                   -- issue | pr | discussion | post | show
    title           TEXT NOT NULL,
    body            TEXT,
    url             TEXT,
    author          TEXT,
    created_at      TEXT,                   -- ISO8601 UTC
    score_raw       INTEGER DEFAULT 0,      -- stars / upvotes / points
    num_comments    INTEGER DEFAULT 0,
    velocity        REAL DEFAULT 0,         -- engagement units per hour since created
    community_size  INTEGER DEFAULT 0,      -- followers / subscribers / repo stars
    effort          REAL DEFAULT 0.5,       -- 0 (trivial) .. 1 (high effort) to contribute
    tags            TEXT                    -- JSON array of keyword tags
);
CREATE INDEX IF NOT EXISTS idx_opp_domain ON opportunities(domain);
CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source);

CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    interests    TEXT,                      -- JSON array of domain keys
    time_budget  REAL DEFAULT 5.0,          -- hours per week
    platforms    TEXT,                      -- JSON array
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT,
    opp_id     TEXT,
    action     TEXT,                        -- engage | bookmark | skip
    reward     REAL,
    ts         TEXT
);
CREATE INDEX IF NOT EXISTS idx_fb_user ON feedback(user_id);

-- Persisted LinUCB state so learning survives app reloads / redeploys.
CREATE TABLE IF NOT EXISTS bandit_state (
    user_id   TEXT PRIMARY KEY,
    blob      BLOB,
    updated_at TEXT
);
"""

REWARD = {"engage": 1.0, "bookmark": 2.0, "skip": -1.0}


def connect(db_path: str | os.PathLike = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | os.PathLike = DB_PATH) -> sqlite3.Connection:
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def load_domains() -> dict:
    import yaml
    with open(DOMAINS_YAML) as f:
        return yaml.safe_load(f)


# ── Production plumbing (added per Lecture 10: env config, logging, versioning) ──
import logging as _logging

# Index/model version. Bump when the embedding space changes so the app can warn
# if a stale index is loaded against new code (reproducibility, MLOps model layer).
MODEL_VERSION = os.environ.get("ENGAGEIQ_MODEL_VERSION", "2025.06-tfidf-svd256")

def get_logger(name: str = "engageiq") -> _logging.Logger:
    """Structured-ish logger. Detailed logs internally; user-facing code shows
    generic messages (Lecture 10: 'generic to users, structured logs internally')."""
    log = _logging.getLogger(name)
    if not log.handlers:
        h = _logging.StreamHandler()
        h.setFormatter(_logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s :: %(message)s", "%H:%M:%S"))
        log.addHandler(h)
        log.setLevel(os.environ.get("ENGAGEIQ_LOG_LEVEL", "INFO"))
    return log


def require_env(key: str) -> str:
    """Read a secret from the environment and crash loudly if it's missing —
    never hardcode (Lecture 10 secrets rule). Returns the value if present."""
    val = os.environ.get(key)
    if not val:
        raise SystemExit(f"Missing required env var {key}. Set it; do not hardcode.")
    return val
