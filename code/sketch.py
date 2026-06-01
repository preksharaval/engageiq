"""
sketch.py — probabilistic data structures from BAX-423 Lecture 2 (sketching).

Two sketches, both dependency-free (hashlib, so they install/run anywhere):
  • BloomFilter      — O(1) approximate set membership; fast first-pass exact-dedup
                       gate in the streaming pipeline (no false negatives).
  • CountMinSketch   — O(1) approximate frequency; powers trending-keyword analytics
                       without holding a full term->count dict in memory.

These complement the MinHash-LSH near-dup detector: Bloom catches exact repeats
cheaply, MinHash catches reworded cross-posts. Two sketches, two jobs.
"""
from __future__ import annotations
import math, hashlib


def _hashes(item: str, k: int, m: int):
    """k independent hash positions in [0, m) from one SHA-256 digest (double hashing)."""
    item = str(item).encode("utf-8")
    h1 = int.from_bytes(hashlib.sha256(item).digest()[:8], "big")
    h2 = int.from_bytes(hashlib.sha256(item + b"salt").digest()[:8], "big") | 1
    for i in range(k):
        yield (h1 + i * h2) % m


class BloomFilter:
    """Space-efficient probabilistic set membership. 'Definitely no' or 'probably yes';
    never a false negative. Sized from expected n and target false-positive prob."""

    def __init__(self, n: int = 100_000, fpp: float = 0.005):
        if not 0 < fpp < 1:
            raise ValueError("fpp must be in (0,1)")
        self.n = max(1, n)
        self.fpp = fpp
        self.m = math.ceil(-self.n * math.log(fpp) / (math.log(2) ** 2))
        self.k = max(1, round((self.m / self.n) * math.log(2)))
        self.bits = bytearray(math.ceil(self.m / 8))
        self.inserted = 0

    def add(self, item: str) -> None:
        for pos in _hashes(item, self.k, self.m):
            self.bits[pos // 8] |= (1 << (pos % 8))
        self.inserted += 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[pos // 8] & (1 << (pos % 8))
                   for pos in _hashes(item, self.k, self.m))

    def current_fpp(self) -> float:
        return (1 - math.exp(-self.k * self.inserted / self.m)) ** self.k

    def memory_bytes(self) -> int:
        return len(self.bits)


class CountMinSketch:
    """Approximate frequency estimator. Never undercounts (estimate >= true count),
    bounded over-count with high probability. Used for trending-keyword frequency."""

    def __init__(self, epsilon: float = 0.001, delta: float = 0.01):
        self.w = math.ceil(math.e / epsilon)
        self.d = math.ceil(math.log(1 / delta))
        self.table = [[0] * self.w for _ in range(self.d)]
        self.total = 0

    def update(self, item: str, count: int = 1) -> None:
        for row, pos in enumerate(_hashes(item, self.d, self.w)):
            self.table[row][pos] += count
        self.total += count

    def query(self, item: str) -> int:
        return min(self.table[row][pos]
                   for row, pos in enumerate(_hashes(item, self.d, self.w)))

    def memory_bytes(self) -> int:
        return self.d * self.w * 8


if __name__ == "__main__":
    bf = BloomFilter(n=1000, fpp=0.01)
    bf.add("kubernetes/kubernetes")
    print("bloom: present? ", "kubernetes/kubernetes" in bf,
          "| absent?", "torvalds/linux" in bf,
          "| mem", bf.memory_bytes(), "bytes")
    cms = CountMinSketch()
    for w in ["llm", "llm", "llm", "rag", "kafka"]:
        cms.update(w)
    print("cms: llm~", cms.query("llm"), " rag~", cms.query("rag"),
          " mem", cms.memory_bytes(), "bytes")
