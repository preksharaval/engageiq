"""
benchmarks.py — quantify the two BAX-423 techniques vs baselines.

(1) Retrieval quality + speed:
      embedding (SVD/SBERT) + FAISS ANN   vs   raw TF-IDF cosine (lexical baseline)
      metric: Recall@50 against proxy-gold (domain + keyword) labels; mean query latency.
(2) Adaptive learning:
      LinUCB contextual bandit   vs   static composite ranker (no learning)
      metric: cumulative reward over 50 rounds per persona; crossover round.

Writes charts to data/bench_recall.png and data/bench_reward.png and prints a summary.
"""
from __future__ import annotations
import sys, time, json, math
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import connect, DATA  # noqa: E402
from score.composite import Ranker  # noqa: E402
from learn.bandit import LinUCB, feat  # noqa: E402
from eval.personas import PERSONAS  # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ----------------------------------------------------------------------
# (1) Retrieval quality + speed
# ----------------------------------------------------------------------
def _gold_ids(ranker: Ranker, interests, kw_expand) -> set:
    """Gold = in-domain items whose text mentions a profile keyword.
    This is the semantic relevance signal a good retriever should surface."""
    kw_lower = {k.lower() for k in kw_expand}
    gold = set()
    for oid, m in ranker.meta.items():
        if m["domain"] in interests:
            text = ((m["title"] or "") + " " + (m["body"] or "")).lower()
            if any(k in text for k in kw_lower):
                gold.add(oid)
    return gold


def bench_retrieval(ranker: Ranker | None = None):
    ranker = ranker or Ranker()
    cfg = ranker.cfg

    # lexical TF-IDF baseline over the same corpus
    from sklearn.feature_extraction.text import TfidfVectorizer
    conn = connect()
    rows = conn.execute("SELECT id, title, body FROM opportunities ORDER BY id").fetchall()
    conn.close()
    ids = [r["id"] for r in rows]
    texts = [(r["title"] or "") + " " + (r["body"] or "")[:512] for r in rows]
    tfidf = TfidfVectorizer(max_features=8192, ngram_range=(1, 2), stop_words="english", min_df=2)
    M = tfidf.fit_transform(texts)  # sparse, rows already L2 by default

    emb_recalls, lex_recalls, faiss_lat, np_lat = [], [], [], []
    ndcg10s, prec10s = [], []
    for p in PERSONAS:
        interests = set(p["profile"]["interests"])
        kw_expand = set()
        for d in p["profile"]["interests"]:
            kw_expand |= set(cfg["domains"][d]["keywords"])
        gold = _gold_ids(ranker, interests, kw_expand)
        if not gold:
            continue
        denom = min(50, len(gold))

        qvec = ranker.encode_profile(p["profile"]["interests"], p["profile"]["free_text"])

        # embedding + FAISS top-50
        t0 = time.perf_counter()
        emb_hits = ranker.retrieve(qvec, k=50)
        faiss_lat.append((time.perf_counter() - t0) * 1000)
        emb_top = {oid for oid, _ in emb_hits}
        emb_recalls.append(len(emb_top & gold) / denom)

        # NDCG@10 and Precision@10 on the ranked FAISS list (Lecture 7 metrics).
        # binary relevance: an item is relevant if it's in the gold set.
        ranked_ids = [oid for oid, _ in emb_hits[:10]]
        rels = [1.0 if oid in gold else 0.0 for oid in ranked_ids]
        dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rels))
        ideal = sorted(rels, reverse=True)
        idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal)) or 1.0
        ndcg10s.append(dcg / idcg)
        prec10s.append(sum(rels) / 10.0)

        # embedding brute-force numpy (latency baseline, same vectors)
        t0 = time.perf_counter()
        sims = ranker.emb @ qvec.astype("float32")
        np.argpartition(-sims, 50)[:50]
        np_lat.append((time.perf_counter() - t0) * 1000)

        # lexical TF-IDF cosine top-50
        qtext = " ".join(cfg["domains"][d]["label"] for d in p["profile"]["interests"]) + " " + p["profile"]["free_text"]
        qv = tfidf.transform([qtext])
        cos = (M @ qv.T).toarray().ravel()
        lex_top = {ids[i] for i in np.argpartition(-cos, 50)[:50]}
        lex_recalls.append(len(lex_top & gold) / denom)

    summary = {
        "embedding_faiss_recall@50": round(float(np.mean(emb_recalls)), 3),
        "tfidf_lexical_recall@50": round(float(np.mean(lex_recalls)), 3),
        "embedding_ndcg@10": round(float(np.mean(ndcg10s)), 3),
        "embedding_precision@10": round(float(np.mean(prec10s)), 3),
        "faiss_latency_ms": round(float(np.mean(faiss_lat)), 3),
        "numpy_bruteforce_latency_ms": round(float(np.mean(np_lat)), 3),
        "embedder_backend": ranker.enc.backend,
    }

    # chart
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.bar(["Embedding+FAISS\n(our system)", "TF-IDF lexical\n(baseline)"],
           [summary["embedding_faiss_recall@50"], summary["tfidf_lexical_recall@50"]],
           color=["#2563eb", "#94a3b8"])
    ax.set_ylim(0, 1); ax.set_ylabel("Recall@50 (proxy gold)")
    ax.set_title(f"Retrieval quality  (backend: {ranker.enc.backend})")
    for i, v in enumerate([summary["embedding_faiss_recall@50"], summary["tfidf_lexical_recall@50"]]):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontweight="bold")
    fig.tight_layout(); fig.savefig(DATA / "bench_recall.png", dpi=130); plt.close(fig)
    return summary


# ----------------------------------------------------------------------
# (2) Adaptive learning: LinUCB vs static
# ----------------------------------------------------------------------
def _hidden_reward(opp: dict, persona: dict) -> float:
    """A latent user taste the system does NOT see directly. Bandit must infer it."""
    pid = persona["profile"]["user_id"]
    src, eff = opp["source"], opp["effort"]
    if pid == "sofia":          # loves low-effort github ML contributions
        if src == "github" and eff < 0.5: return 2.0
        if src == "github": return 1.0
        return -1.0
    if pid == "david":          # loves lively github K8s discussions, high community health
        if src == "github" and opp["components"]["community_health"] > 0.1: return 2.0
        if src == "github": return 1.0
        return -1.0
    if pid == "lina":           # loves high-velocity trending items
        return 2.0 if opp["velocity"] > 5 else (1.0 if opp["velocity"] > 1 else -1.0)
    if pid == "raj":            # loves high-visibility, low-effort devtools
        if opp["components"]["visibility_potential"] > 0.5 and eff < 0.65: return 2.0
        if opp["components"]["visibility_potential"] > 0.5: return 1.0
        return -1.0
    return 0.0


def bench_bandit(ranker: Ranker | None = None, rounds: int = 50):
    ranker = ranker or Ranker()
    curves = {}
    crossovers = {}
    for p in PERSONAS:
        pool = ranker.rank(p["profile"]["interests"], p["profile"]["free_text"],
                           source_affinity=p.get("profile",{}).get("source_affinity",{}), topn=80)
        if len(pool) < rounds:
            pool = pool * (rounds // max(1, len(pool)) + 1)

        # static: fixed composite order
        static_cum, s = [], 0.0
        for t in range(rounds):
            s += _hidden_reward(pool[t], p); static_cum.append(s)

        # bandit: pick UCB-best unseen item each round, observe hidden reward, update
        model = LinUCB(alpha=0.35)
        seen = set(); b = 0.0; bandit_cum = []
        for t in range(rounds):
            best, best_u, best_i = None, -1e9, -1
            for i, o in enumerate(pool):
                if i in seen: continue
                u = model.ucb(feat(o))
                if u > best_u: best_u, best, best_i = u, o, i
            seen.add(best_i)
            r = _hidden_reward(best, p)
            model.update(feat(best), r)
            b += r; bandit_cum.append(b)

        curves[p["profile"]["user_id"]] = (static_cum, bandit_cum)
        cross = next((t for t in range(rounds) if bandit_cum[t] > static_cum[t]), None)
        crossovers[p["profile"]["user_id"]] = cross

    # chart: 2x2 grid
    fig, axes = plt.subplots(2, 2, figsize=(8, 5.6), sharex=True)
    for ax, p in zip(axes.ravel(), PERSONAS):
        sc, bc = curves[p["profile"]["user_id"]]
        ax.plot(range(1, rounds + 1), sc, label="static", color="#94a3b8", lw=2)
        ax.plot(range(1, rounds + 1), bc, label="LinUCB", color="#2563eb", lw=2)
        ax.set_title(p["name"].split(" — ")[0] + f"  (cross@{crossovers[p['profile']['user_id']]})", fontsize=9)
        ax.grid(alpha=.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Cumulative reward: LinUCB bandit vs static ranker (50 rounds)")
    fig.supxlabel("round"); fig.supylabel("cumulative reward")
    fig.tight_layout(); fig.savefig(DATA / "bench_reward.png", dpi=130); plt.close(fig)

    final = {p["profile"]["user_id"]: {"static": curves[p["profile"]["user_id"]][0][-1],
                       "bandit": curves[p["profile"]["user_id"]][1][-1],
                       "crossover_round": crossovers[p["profile"]["user_id"]]} for p in PERSONAS}
    return final


if __name__ == "__main__":
    r = Ranker()
    print("== retrieval ==")
    rs = bench_retrieval(r)
    for k, v in rs.items(): print(f"  {k}: {v}")
    print("== bandit vs static ==")
    bs = bench_bandit(r)
    for pid, v in bs.items(): print(f"  {pid}: {v}")
    print("charts -> data/bench_recall.png, data/bench_reward.png")
