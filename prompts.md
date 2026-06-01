# prompts.md — Key AI Prompts Used (EngageIQ)

BAX-423 encourages AI assistance. Per the brief, each entry is one prompt with a
sentence on its **purpose** and **how I modified the output**. Assistant: Claude.

1. **"Pick the best option among NutriAI / JobPilot / EngageIQ and give a 3-day shippable plan hitting all 6 capabilities and >=2 benchmarked techniques."**
   *Purpose:* choose a project and scope. *Modification:* I overrode its initial 7-day plan and compressed it to my own schedule, and locked the stack to Streamlit + SQLite + FAISS.

2. **"Generate a domains.yaml with exactly the 15 brief domains (Machine Learning, DevOps/K8s, ..., Beginner Coding), each with keywords, subreddits, GitHub queries, and HN terms."**
   *Purpose:* domain taxonomy driving ingestion + tagging. *Modification:* I corrected the labels to match the brief verbatim and added good-first-issue GitHub queries for the Beginner Coding domain.

3. **"Write GitHub REST + Hacker News + Reddit (PRAW) ingestion scripts that emit data/raw/*.jsonl and tag each record to one of the 15 domains."**
   *Purpose:* real multi-source ingestion. *Modification:* I added a has_good_first_issue flag and a separate GitHub issues query so Sofia's persona criteria could be satisfied.

4. **"Write a streaming ingestion pipeline (StreamProcessor) that consumes records one-by-one, applies online MinHash-LSH dedup, and commits to SQLite incrementally; support a --replay mode."**
   *Purpose:* satisfy Capability 1's real-time streaming requirement. *Modification:* I added running dedup stats and a rolling window so the dashboard can show a live-ingest indicator.

5. **"Implement near-duplicate dedup with MinHash-LSH (datasketch, 64 perms, 3-gram shingles, threshold 0.82) over the merged raw files."**
   *Purpose:* dedup cross-posts that exact-URL matching misses. *Modification:* I tuned the threshold from the suggested 0.9 down to 0.82 after it missed reworded cross-posts in testing.

6. **"Build a unified encoder using Sentence-BERT when available, falling back to TF-IDF + TruncatedSVD(256) offline, then a FAISS IndexFlatIP for cosine retrieval."**
   *Purpose:* embeddings + ANN retrieval (Technique 1). *Modification:* I added the persisted TF-IDF fallback so the app runs in environments without the SBERT model download.

7. **"Implement a composite scorer = 0.50*relevance + 0.20*community_health + 0.20*visibility + 0.10*(1-effort) and return each component's contribution for a 'Why this?' panel."**
   *Purpose:* transparent multi-signal ranking (Capability 3). *Modification:* I added a source-affinity boost so platform-focused personas (e.g. Sofia -> GitHub) rank correctly.

8. **"Add a per-user LinUCB contextual bandit that re-ranks from engage/bookmark/skip feedback; persist A and b per user in SQLite."**
   *Purpose:* adaptive learning (Technique 2). *Modification:* I lowered the exploration alpha to 0.35 after the benchmark showed too much exploration kept the bandit below the static baseline for one persona.

9. **"Encode Sofia/David/Lina/Raj as executable pass/fail tests matching the brief's exact criteria (e.g. >=3 good-first-issue repos, no C++/Rust, <1hr effort)."**
   *Purpose:* persona validation + hidden-persona robustness. *Modification:* I rewrote the thresholds against real value distributions so the checks reflect the brief rather than arbitrary cutoffs.

10. **"Write benchmarks: Recall@50 embedding+FAISS vs TF-IDF lexical, retrieval latency, and a 50-round LinUCB-vs-static cumulative-reward simulation per persona with crossover round."**
    *Purpose:* required ranking + learning benchmarks. *Modification:* I fixed the gold-set definition to text-based relevance after the first version under-counted recall.

11. **"Add batch trend analytics: trending topics, growing domains, source mix, and engagement volume over time, rendered as Plotly charts."**
    *Purpose:* Capability 5 batch analytics. *Modification:* I switched the trend window to week-over-week deltas to satisfy Lina's persona criterion.

12. **"Generate a downloadable weekly engagement brief (reportlab PDF + CSV) of the top opportunities, and a template-based Suggested Action that uses Claude-Haiku only if ANTHROPIC_API_KEY is set."**
    *Purpose:* Capability 6 exportable brief + suggested actions. *Modification:* I made the LLM path optional so the app has zero paid dependencies by default.

13. **"Build the Streamlit dashboard with a dark 3D glassmorphism theme: animated opportunity cards, a 3D opportunity-space scatter, Why-this bars, feedback buttons, trends, and brief export."**
    *Purpose:* the user-facing UI (Capability 6 + hosting). *Modification:* I chose the 3D/glassmorphism direction specifically and iterated the colors and card animations.

14. **"Write a <=4-page technical brief PDF: architecture, the 6 capabilities, both techniques with benchmark tables/charts, the 4-persona pass/fail table, dataset stats, and limitations."**
    *Purpose:* the graded brief deliverable. *Modification:* I added the deployment-URL and GitHub-link fields and the pipeline-design section the rubric asks for.

15. **"Treat the project as a prototype-to-production exercise (Lecture 10): add explicit cold-start handling, pytest tests + a CI workflow that gates deploys, data validation + drift monitoring, env-var secrets, and input validation/error handling."**
    *Purpose:* make the app stand out as production-grade, not just a demo. *Modification:* I removed an accidental hardcoded GitHub-token fallback the assistant left in, added a test that fails the build if any secret is hardcoded, and tuned the cold-start trust ramp (0.15 → 0.60) myself.

16. **"Cross-check the project against the course knowledge base and close real technique gaps: add NDCG@10 + Precision@10 (L7), a Bloom filter first-pass dedup alongside MinHash (L2), a Count-Min Sketch for trending keywords (L2), and an explicit diversity re-rank stage (L6)."**
    *Purpose:* broaden course-technique coverage to 5 techniques across 4 lectures and add the ranking metrics the brief asks for. *Modification:* I made the Bloom filter and Count-Min Sketch dependency-free (hashlib, not mmh3) so deployment can't break, and kept the DCN/Q-learning out on purpose — the composite+bandit is more explainable for the "Why this?" deliverable and lower-risk for the live demo.
