"""
encoder.py — one interface, two backends.

  backend = "sbert"   -> sentence-transformers all-MiniLM-L6-v2 (needs internet on first run)
  backend = "tfidf"   -> TF-IDF + TruncatedSVD (fully offline; fitted on the corpus)

Both return L2-normalized float32 vectors so cosine similarity == inner product.
The fitted state is persisted to data/embedder.pkl so query-time uses the SAME space.
"""
from __future__ import annotations
import pickle
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import DATA  # noqa: E402

EMBEDDER_PKL = DATA / "embedder.pkl"
SBERT_MODEL = "all-MiniLM-L6-v2"


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (x / n).astype("float32")


class Encoder:
    def __init__(self, backend: str, model=None, vectorizer=None, svd=None, dim=None):
        self.backend = backend
        self._model = model            # sbert model (not pickled)
        self.vectorizer = vectorizer   # tfidf fallback
        self.svd = svd                 # tfidf fallback
        self.dim = dim

    # ---- fitting -------------------------------------------------------
    @classmethod
    def fit(cls, texts: list[str], prefer_sbert: bool = True, svd_dim: int = 256) -> "Encoder":
        if prefer_sbert:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(SBERT_MODEL)
                dim = model.get_sentence_embedding_dimension()
                print(f"[encoder] using Sentence-BERT ({SBERT_MODEL}, dim={dim})")
                return cls(backend="sbert", model=model, dim=dim)
            except Exception as e:  # offline / not installed
                print(f"[encoder] SBERT unavailable ({type(e).__name__}); "
                      f"falling back to TF-IDF+SVD. {e}")

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        vec = TfidfVectorizer(max_features=8192, ngram_range=(1, 2),
                              stop_words="english", min_df=2)
        X = vec.fit_transform(texts)
        k = min(svd_dim, X.shape[1] - 1)
        svd = TruncatedSVD(n_components=k, random_state=423)
        svd.fit(X)
        print(f"[encoder] using TF-IDF+SVD (dim={k})")
        return cls(backend="tfidf", vectorizer=vec, svd=svd, dim=k)

    # ---- encoding ------------------------------------------------------
    def encode(self, texts: list[str], batch_size: int = 256) -> np.ndarray:
        if self.backend == "sbert":
            vecs = self._model.encode(texts, batch_size=batch_size,
                                      show_progress_bar=False, convert_to_numpy=True)
            return _l2(np.asarray(vecs, dtype="float32"))
        X = self.vectorizer.transform(texts)
        return _l2(self.svd.transform(X).astype("float32"))

    # ---- persistence ---------------------------------------------------
    def save(self, path: Path = EMBEDDER_PKL):
        state = {"backend": self.backend, "dim": self.dim,
                 "vectorizer": self.vectorizer, "svd": self.svd}
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path = EMBEDDER_PKL) -> "Encoder":
        with open(path, "rb") as f:
            s = pickle.load(f)
        if s["backend"] == "sbert":
            from sentence_transformers import SentenceTransformer
            return cls(backend="sbert", model=SentenceTransformer(SBERT_MODEL), dim=s["dim"])
        return cls(backend="tfidf", vectorizer=s["vectorizer"], svd=s["svd"], dim=s["dim"])
