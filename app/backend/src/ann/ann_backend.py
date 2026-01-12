class AnnUnavailable(Exception):
    """Raised when ANN backend not available."""


class BaseAnnBackend:
    def build(self, vectors, ids):
        raise NotImplementedError

    def search(self, index, query_vec, top_k: int):
        raise NotImplementedError

    def save(self, index, path: str):
        raise NotImplementedError

    def load(self, path: str):
        raise NotImplementedError
