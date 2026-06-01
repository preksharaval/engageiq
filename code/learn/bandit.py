"""
bandit.py — LinUCB contextual bandit for the feedback loop (adaptive learning).

Context per opportunity x (7-dim, cheap + persistable):
    [relevance, community_health, visibility_potential, effort_inv,
     is_github, is_reddit, is_hackernews]

Shared-weight LinUCB:
    A := lambda*I  (d x d),  b := 0
    theta = A^-1 b
    ucb(x) = theta·x + alpha * sqrt(x^T A^-1 x)
    update(x, r): A += x x^T ; b += r x

Reward: engage=+1, bookmark=+2, skip=-1. State is pickled per user into
the bandit_state table so learning survives app reloads / redeploys.
"""
from __future__ import annotations
import sys, pickle, datetime as dt
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import connect, REWARD  # noqa: E402

SOURCES = ["github", "reddit", "hackernews"]
DIM = 7


def feat(opp: dict) -> np.ndarray:
    c = opp["components"]
    src = opp["source"]
    return np.array([
        c["relevance"], c["community_health"],
        c["visibility_potential"], c["effort_inv"],
        1.0 if src == "github" else 0.0,
        1.0 if src == "reddit" else 0.0,
        1.0 if src == "hackernews" else 0.0,
    ], dtype="float64")


class LinUCB:
    def __init__(self, dim: int = DIM, alpha: float = 0.6, lam: float = 1.0):
        self.dim = dim
        self.alpha = alpha
        self.A = lam * np.eye(dim)
        self.b = np.zeros(dim)
        self.n_updates = 0          # how much feedback this user has given

    # A user is "cold" until they've given enough feedback for the bandit to
    # be trustworthy. Until then we lean on the composite score (sensible
    # defaults) instead of a half-trained model — the Job-Rec cold-start lesson.
    COLD_START_THRESHOLD = 5

    @property
    def is_cold(self) -> bool:
        return self.n_updates < self.COLD_START_THRESHOLD

    def trust(self) -> float:
        """How much to weight the bandit vs the composite. Ramps 0.15 -> 0.6 as
        feedback accrues, so a brand-new user never gets erratic recommendations."""
        if self.n_updates == 0:
            return 0.15
        return float(min(0.6, 0.15 + 0.09 * self.n_updates))

    def _theta(self):
        return np.linalg.solve(self.A, self.b)

    def ucb(self, x: np.ndarray) -> float:
        Ainv = np.linalg.inv(self.A)
        theta = Ainv @ self.b
        mean = float(theta @ x)
        bonus = self.alpha * float(np.sqrt(max(0.0, x @ Ainv @ x)))
        return mean + bonus

    def update(self, x: np.ndarray, reward: float):
        self.A += np.outer(x, x)
        self.b += reward * x
        self.n_updates += 1

    # ---- persistence ---------------------------------------------------
    def dumps(self) -> bytes:
        return pickle.dumps({"dim": self.dim, "alpha": self.alpha,
                             "A": self.A, "b": self.b, "n_updates": self.n_updates})

    @classmethod
    def loads(cls, blob: bytes) -> "LinUCB":
        s = pickle.loads(blob)
        m = cls(dim=s["dim"], alpha=s["alpha"])
        m.A, m.b = s["A"], s["b"]
        m.n_updates = s.get("n_updates", int(round(np.trace(s["A"]) - s["dim"])))
        return m


# ---- store helpers -----------------------------------------------------
def load_bandit(user_id: str, alpha: float = 0.6) -> LinUCB:
    conn = connect()
    row = conn.execute("SELECT blob FROM bandit_state WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["blob"]:
        return LinUCB.loads(row["blob"])
    return LinUCB(alpha=alpha)


def save_bandit(user_id: str, model: LinUCB):
    conn = connect()
    conn.execute(
        "INSERT OR REPLACE INTO bandit_state(user_id, blob, updated_at) VALUES (?,?,?)",
        (user_id, model.dumps(), dt.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def record_feedback(user_id: str, opp: dict, action: str):
    """Log feedback and update the user's bandit in one shot."""
    reward = REWARD.get(action, 0.0)
    conn = connect()
    conn.execute(
        "INSERT INTO feedback(user_id, opp_id, action, reward, ts) VALUES (?,?,?,?,?)",
        (user_id, opp["id"], action, reward, dt.datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    model = load_bandit(user_id)
    model.update(feat(opp), reward)
    save_bandit(user_id, model)
    return reward


def make_rerank_fn(model: LinUCB, blend: float | None = None):
    """Return a rerank_fn for Ranker.rank that blends static composite with bandit UCB.

    `blend` defaults to the model's adaptive trust(): a cold user leans on the
    composite score; the bandit's influence grows only as real feedback arrives.
    Pass an explicit float to override (used in benchmarks)."""
    def rerank(scored: list[dict]) -> list[dict]:
        if not scored:
            return scored
        w = blend if blend is not None else model.trust()
        ucbs = np.array([model.ucb(feat(o)) for o in scored])
        # normalize UCB to [0,1] to blend with composite (already ~[0,1])
        lo, hi = float(ucbs.min()), float(ucbs.max())
        norm = (ucbs - lo) / (hi - lo) if hi - lo > 1e-9 else np.zeros_like(ucbs)
        for o, u in zip(scored, norm):
            o["bandit_ucb"] = float(u)
            o["final"] = (1 - w) * o["composite"] + w * float(u)
            o["cold_start"] = model.is_cold
        scored.sort(key=lambda x: x["final"], reverse=True)
        return scored
    return rerank
