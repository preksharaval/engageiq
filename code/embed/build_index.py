"""
build_index.py — embed every opportunity (title + body[:512]) and build an ANN index.

Outputs:
  data/embeddings.npy      float32 [N, dim], L2-normalized
  data/embedding_ids.npy   object  [N] opportunity ids aligned to rows
  data/faiss.index         FAISS IndexFlatIP (cosine via normalized vectors)
  data/embedder.pkl        fitted encoder state (for query-time encoding)

If faiss is missing, embeddings.npy alone is enough: the ranker falls back to a
numpy inner-product search.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import connect, EMB_PATH, IDS_PATH, FAISS_PATH  # noqa: E402
from embed.encoder import Encoder  # noqa: E402


def opportunity_text(title: str, body: str | None) -> str:
    return (title or "").strip() + " " + (body or "")[:512]


def build(prefer_sbert: bool = True):
    conn = connect()
    rows = conn.execute(
        "SELECT id, title, body FROM opportunities ORDER BY id"
    ).fetchall()
    conn.close()
    if not rows:
        raise SystemExit("No opportunities found — run ingest/make_snapshot.py first.")

    ids = np.array([r["id"] for r in rows], dtype=object)
    texts = [opportunity_text(r["title"], r["body"]) for r in rows]
    print(f"[build_index] encoding {len(texts)} documents ...")

    enc = Encoder.fit(texts, prefer_sbert=prefer_sbert)
    emb = enc.encode(texts)
    enc.save()

    np.save(EMB_PATH, emb)
    np.save(IDS_PATH, ids)
    print(f"[build_index] embeddings {emb.shape} -> {EMB_PATH.name}")

    try:
        import faiss
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb)
        faiss.write_index(index, str(FAISS_PATH))
        print(f"[build_index] FAISS IndexFlatIP with {index.ntotal} vectors -> {FAISS_PATH.name}")
    except Exception as e:
        print(f"[build_index] faiss unavailable ({e}); ranker will use numpy fallback.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sbert", action="store_true", help="force TF-IDF+SVD fallback")
    args = ap.parse_args()
    build(prefer_sbert=not args.no_sbert)
