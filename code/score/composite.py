"""
composite.py — retrieval + transparent composite scoring.

composite = 0.50 * relevance            (cosine to the user's interest profile)
          + 0.20 * community_health     (how alive the discussion is: comments + velocity)
          + 0.20 * visibility_potential (reach if you engage: source prior x audience size)
          + 0.10 * (1 - effort)         (lower effort to contribute -> higher score)

Every component is returned alongside the score so the UI can render "Why this?".
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import connect, EMB_PATH, IDS_PATH, FAISS_PATH, load_domains  # noqa: E402
from embed.encoder import Encoder  # noqa: E402

WEIGHTS = {"relevance": 0.50, "community_health": 0.20,
           "visibility_potential": 0.20, "effort": 0.10}


def _minmax(v: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(v)), float(np.max(v))
    if hi - lo < 1e-9:
        return np.zeros_like(v)
    return (v - lo) / (hi - lo)


class Ranker:
    def __init__(self):
        self.enc = Encoder.load()
        self.emb = np.load(EMB_PATH)
        self.ids = np.load(IDS_PATH, allow_pickle=True)
        self.id_to_row = {i: r for r, i in enumerate(self.ids)}
        self.cfg = load_domains()
        self.src_prior = self.cfg.get("source_visibility_prior",
                                      {"github": .85, "hackernews": .95, "reddit": .70})
        self._faiss = None
        try:
            import faiss
            self._faiss = faiss.read_index(str(FAISS_PATH))
        except Exception:
            self._faiss = None  # numpy fallback
        self._load_meta()

    def _load_meta(self):
        """Pull per-record metadata + precompute corpus-normalized priors."""
        conn = connect()
        rows = conn.execute(
            """SELECT id, source, domain, opp_type, title, body, url, author,
                      created_at, score_raw, num_comments, velocity,
                      community_size, effort, tags, has_good_first_issue FROM opportunities"""
        ).fetchall()
        conn.close()
        self.meta = {r["id"]: dict(r) for r in rows}
        ncom = np.array([np.log1p(self.meta[i]["num_comments"]) for i in self.ids])
        vel = np.array([np.log1p(self.meta[i]["velocity"]) for i in self.ids])
        reach = np.array([np.log1p(self.meta[i]["community_size"]) for i in self.ids])
        ncom_n, vel_n, reach_n = _minmax(ncom), _minmax(vel), _minmax(reach)
        for k, i in enumerate(self.ids):
            m = self.meta[i]
            m["_health"] = float(0.5 * ncom_n[k] + 0.5 * vel_n[k])
            m["_reach"] = float(reach_n[k])

    # ---- query embedding ----------------------------------------------
    def encode_profile(self, interests: list[str], free_text: str = "") -> np.ndarray:
        labels = [self.cfg["domains"][d]["label"] for d in interests if d in self.cfg["domains"]]
        kws = []
        for d in interests:
            if d in self.cfg["domains"]:
                kws += self.cfg["domains"][d]["keywords"][:5]
        # Repeat free_text 3x so goal/role words have real influence over domain terms
        ft_boosted = (" " + free_text.strip()) * 3 if free_text.strip() else ""
        text = " ".join(labels + kws) + ft_boosted
        return self.enc.encode([text])[0]

    # ---- retrieval -----------------------------------------------------
    def retrieve(self, qvec: np.ndarray, k: int = 400):
        q = qvec.reshape(1, -1).astype("float32")
        if self._faiss is not None:
            sims, idx = self._faiss.search(q, k)
            return [(self.ids[i], float(s)) for s, i in zip(sims[0], idx[0]) if i >= 0]
        sims = (self.emb @ q[0])
        top = np.argpartition(-sims, min(k, len(sims) - 1))[:k]
        top = top[np.argsort(-sims[top])]
        return [(self.ids[i], float(sims[i])) for i in top]

    # ---- full ranking --------------------------------------------------
    def rank(self, interests, free_text="", time_budget=5.0, platforms=None,
             topn=50, candidate_k=400, rerank_fn=None, source_affinity=None,
             diversity=False, diversity_decay=0.85):
        qvec = self.encode_profile(interests, free_text)
        cands = self.retrieve(qvec, k=candidate_k)
        interest_set = set(interests)
        platforms = set(platforms or [])
        # Soft preference for where the user wants to focus (e.g. a portfolio builder
        # leans GitHub). A nudge, not a hard filter, so diversity is preserved.
        source_affinity = source_affinity or {}
        AFFINITY_W = 0.18

        scored = []
        for oid, sim in cands:
            m = self.meta[oid]
            if interest_set and m["domain"] not in interest_set:
                continue
            if platforms and m["source"] not in platforms:
                continue
            relevance = max(0.0, sim)
            health = m["_health"]
            visibility = self.src_prior.get(m["source"], 0.7) * m["_reach"]
            effort_term = 1.0 - float(m["effort"])
            comp = (WEIGHTS["relevance"] * relevance
                    + WEIGHTS["community_health"] * health
                    + WEIGHTS["visibility_potential"] * visibility
                    + WEIGHTS["effort"] * effort_term)
            comp += AFFINITY_W * float(source_affinity.get(m["source"], 0.0))
            scored.append({
                "id": oid, "source": m["source"], "domain": m["domain"],
                "opp_type": m["opp_type"], "title": m["title"], "body": m["body"],
                "url": m["url"], "author": m["author"], "created_at": m["created_at"],
                "score_raw": m["score_raw"], "num_comments": m["num_comments"],
                "velocity": m["velocity"], "community_size": m["community_size"],
                "effort": m["effort"], "tags": json.loads(m["tags"] or "[]"),
                "has_good_first_issue": bool(m.get("has_good_first_issue", 0)),
                "composite": comp,
                "components": {
                    "relevance": relevance, "community_health": health,
                    "visibility_potential": visibility, "effort_inv": effort_term,
                },
                "contributions": {
                    "relevance": WEIGHTS["relevance"] * relevance,
                    "community_health": WEIGHTS["community_health"] * health,
                    "visibility_potential": WEIGHTS["visibility_potential"] * visibility,
                    "effort": WEIGHTS["effort"] * effort_term,
                },
            })

        scored.sort(key=lambda x: x["composite"], reverse=True)
        if rerank_fn is not None:
            scored = rerank_fn(scored)          # Stage 3a: bandit rerank (adaptive learning)
        if diversity:
            scored = self._diversify(scored, decay=diversity_decay)  # Stage 3b: diversity
        scored = self._collapse_near_dupes(scored)  # Stage 3c: one item per title stem
        return scored[:topn]

    @staticmethod
    def _title_stem(title: str) -> str:
        """Normalize a title to its stem so 'Add formatter to language server #267'
        and '#450' collapse to the same key (templated synthetic titles, near-dups)."""
        import re
        t = (title or "").lower()
        t = re.sub(r"#\d+", "", t)            # drop issue/PR numbers
        t = re.sub(r"[^a-z0-9 ]+", " ", t)    # strip punctuation
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @classmethod
    def _collapse_near_dupes(cls, scored):
        """Keep only the highest-ranked item per title stem so the final list shows
        distinct opportunities, not ten variants of the same templated title."""
        seen, out = set(), []
        for o in scored:
            stem = cls._title_stem(o.get("title", ""))
            if stem and stem in seen:
                continue
            seen.add(stem)
            out.append(o)
        return out

    @staticmethod
    def _diversify(scored, decay=0.85):
        """Stage-3 diversity re-rank: penalize repeated source+domain so the list
        doesn't collapse into ten near-identical GitHub repos (Lecture 6 re-ranking).
        score' = score * decay^(times this source+domain already appeared above)."""
        seen = {}
        out = []
        for o in scored:
            key = (o["source"], o.get("domain", ""))
            n = seen.get(key, 0)
            base = o.get("final", o["composite"])
            o["diversified"] = base * (decay ** n)
            seen[key] = n + 1
            out.append(o)
        out.sort(key=lambda x: x["diversified"], reverse=True)
        return out
