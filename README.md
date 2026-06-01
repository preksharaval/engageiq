# EngageIQ — Smart Engagement Opportunity Scorer

BAX-423 Big Data · Spring 2026 · Final Project (Option C) · Preksha Raval

EngageIQ discovers, scores, and ranks **where a professional should invest their
limited time online** across GitHub, Hacker News, and Reddit — across 15 technical
domains. It explains every ranking ("Why this?"), learns from your feedback via a
contextual bandit, shows trends, and exports a downloadable weekly engagement brief.

**Live demo:** &lt;paste your Streamlit Cloud URL here and in brief.pdf&gt;
**GitHub:** &lt;paste your repo URL here and in brief.pdf&gt;

---

## Run it (single command, offline — no API keys needed)

```bash
pip install -r requirements.txt && streamlit run code/app.py
```

The repo ships a prebuilt snapshot (`data/engageiq.sqlite` + `embeddings.npy` +
`faiss.index`, 10,995 records across all 15 domains) so it runs immediately with
zero API access. Streamlit prints a local URL — open it and the demo is live.

> Rebuild the snapshot + index from scratch (optional):
> ```bash
> python code/ingest/make_snapshot.py   # -> data/engageiq.sqlite
> python code/embed/build_index.py      # -> embeddings.npy + faiss.index
> ```

---

## Verify everything works

```bash
pytest tests/ -v                             # 12 regression tests (data, ranking, dedup, cold-start)
python code/eval/personas.py                 # 4/4 personas PASS
python code/eval/benchmarks.py               # Recall@50 + bandit-vs-static + charts
python code/ingest/stream_pipeline.py --replay --limit 3000   # streaming + dedup demo
python code/monitoring.py                    # data validation + freshness + drift health check
```

Expected: 12 tests pass · personas 4/4 PASS · Recall@50 ≈ 0.99 (FAISS) vs 0.74 (lexical) ·
streaming ≈ 1,400+ rec/s with ~4% dedup. CI (`.github/workflows/ci.yml`) runs the tests
and persona check on every push so a broken commit never reaches the live demo.

---

## Refresh with live data (already done for GitHub; re-run anytime)

```bash
export GITHUB_TOKEN=ghp_xxx                   # github.com/settings/tokens (public_repo)
export REDDIT_CLIENT_ID=xxx                   # reddit.com/prefs/apps (script app)
export REDDIT_CLIENT_SECRET=xxx
export REDDIT_USER_AGENT="engageiq by u/you"

python code/ingest/gh_ingest.py               # GitHub REST  -> data/raw/github_real.jsonl
python code/ingest/hn_ingest.py               # Hacker News  -> data/raw/hn_real.jsonl
python code/ingest/reddit_ingest.py           # Reddit/PRAW  -> data/raw/reddit_real.jsonl
python code/ingest/normalize.py               # merge + MinHash-LSH dedup -> SQLite
python code/embed/build_index.py              # rebuild embeddings + FAISS index
```

`code/domains.yaml` controls the 15 domains and per-source queries — edit to tune.

---

## Optional: Claude-written "Suggested Action"

```bash
export ANTHROPIC_API_KEY=sk-ant-xxx           # otherwise a free template is used
```

---

## Deploy to Streamlit Community Cloud (free, ~5 min)

1. Push this repo to GitHub.
2. Go to **share.streamlit.io → Create app → from GitHub**.
3. Repo = your repo, Branch = `main`, **Main file path = `code/app.py`**.
4. (Optional) add `ANTHROPIC_API_KEY` under **Advanced → Secrets**.
5. **Deploy.** First boot installs `requirements.txt`. Paste the resulting URL into
   `brief.pdf` and the top of this README.

Data files are small (~11 MB each) and commit directly — no Git LFS needed.

---

## Layout

```
engageiq/
├── code/
│   ├── app.py                  # Streamlit entry — the deployed file
│   ├── domains.yaml            # 15 brief domains × per-source queries
│   ├── common.py               # paths, SQLite schema, reward map
│   ├── ingest/                 # gh/hn/reddit ingest · stream_pipeline · normalize · make_snapshot
│   ├── embed/                  # encoder (SBERT|TF-IDF+SVD) + build_index
│   ├── score/composite.py      # FAISS retrieve + composite score + "Why this?"
│   ├── learn/bandit.py         # per-user LinUCB contextual bandit
│   ├── analytics/trends.py     # velocity / volume / source-mix / week-over-week
│   ├── export/                 # brief.py (in-app PDF/CSV) + make_brief_pdf.py (project brief)
│   ├── llm/suggest_action.py   # template or Claude-Haiku suggested action
│   └── eval/                   # personas.py (pass/fail) + benchmarks.py
├── data/                       # engageiq.sqlite + embeddings.npy + faiss.index + charts
├── brief.pdf                   # ≤4-page technical brief
├── prompts.md                  # key prompts + how each output was modified
├── requirements.txt
└── README.md
```

## Six core capabilities → where they live

1. **Multi-source ingestion + streaming** — `ingest/*_ingest.py` + `stream_pipeline.py` (two-stage dedup: Bloom filter exact + MinHash-LSH near-dup).
2. **Embedding + ANN retrieval** — `embed/encoder.py` + `score/composite.py` (FAISS).
3. **Engagement scoring + multi-stage ranking** — `score/composite.py` (candidate→score→rerank), metric in `eval/benchmarks.py`.
4. **Adaptive learning** — `learn/bandit.py` (LinUCB, 50-round benchmark).
5. **Batch analytics + trends** — `analytics/trends.py` (Count-Min Sketch trending keywords) + Trends tab.
6. **Dashboard + engagement brief** — `app.py` + `export/brief.py`.
