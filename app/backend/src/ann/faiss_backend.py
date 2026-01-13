from typing import List, Any
from ann.ann_backend import BaseAnnBackend, AnnUnavailable


class FaissBackend(BaseAnnBackend):
    def __init__(self, dim: int):
        self.dim = dim
        try:
            import faiss  # type: ignore
        except ImportError as e:
            raise AnnUnavailable("faiss not installed") from e
        self.faiss = faiss

    def build(self, vectors: List[List[float]], ids: List[int]):
        faiss = self.faiss
        import numpy as np  # type: ignore

        xb = np.array(vectors, dtype=np.float32)
        # L2 normalize for cosine, then use IP
        faiss.normalize_L2(xb)
        base = faiss.IndexHNSWFlat(self.dim, 32, faiss.METRIC_INNER_PRODUCT)
        base.hnsw.efConstruction = 200
        # Wrap with IDMap so add_with_ids is supported
        index = faiss.IndexIDMap(base)
        index.add_with_ids(xb, np.array(ids, dtype=np.int64))
        base.hnsw.efSearch = 64
        return index

    def search(self, index: Any, query_vec, top_k: int):
        import numpy as np  # type: ignore
        q = np.array([query_vec], dtype=np.float32)
        self.faiss.normalize_L2(q)
        scores, idxs = index.search(q, top_k)
        res = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            res.append((int(idx), float(score)))
        return res

    def save(self, index: Any, path: str):
        self.faiss.write_index(index, path)

    def load(self, path: str):
        return self.faiss.read_index(path)
