from typing import List, Dict, Any, Optional
from pathlib import Path
import sqlite3
import math
from array import array
import time

from db import get_entry, list_entries


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_CACHE = Path.home() / ".cache" / "ai-vocab-notebook"


class SemanticUnavailable(Exception):
    """Raised when semantic features are not available (missing deps/model)."""


_model_cache = {}


def _pack_vec(vec: List[float]) -> bytes:
    arr = array("f", vec)
    return arr.tobytes()


def _unpack_vec(buf: bytes) -> List[float]:
    arr = array("f")
    arr.frombytes(buf)
    return list(arr)


def _ensure_model(model_name: str = DEFAULT_MODEL, cache_folder: Optional[Path] = None):
    if "sentence_transformers" not in globals():
        try:
            import sentence_transformers  # type: ignore  # noqa: F401
        except ImportError as e:
            raise SemanticUnavailable("sentence_transformers not installed") from e
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as e:
        raise SemanticUnavailable("sentence_transformers import failed") from e

    key = (model_name, str(cache_folder) if cache_folder else "")
    if key in _model_cache:
        return _model_cache[key]
    model = SentenceTransformer(model_name, cache_folder=str(cache_folder) if cache_folder else None)
    _model_cache[key] = model
    return model


def _encode(model, texts: List[str]):
    try:
        embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    except Exception as e:
        raise SemanticUnavailable("encoding failed") from e
    return embs


def _get_conn(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def ensure_embedding_for_entry(db_path: Path, entry_id: int, model_name: str = DEFAULT_MODEL, cache_folder: Optional[Path] = None):
    model = _ensure_model(model_name, cache_folder)
    entry = get_entry(db_path, entry_id)
    if not entry:
        return False
    text = " ".join([entry.get("word") or "", entry.get("translation") or "", entry.get("notes") or ""]).strip()
    if not text:
        return False
    emb = _encode(model, [text])[0]
    dim = len(emb)
    buf = _pack_vec([float(x) for x in emb])
    now = time.time()
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO entry_embeddings(entry_id, model, dim, vec, updated_at)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(entry_id) DO UPDATE SET model=excluded.model, dim=excluded.dim, vec=excluded.vec, updated_at=excluded.updated_at
        """,
        (entry_id, model_name, dim, sqlite3.Binary(buf), now),
    )
    conn.commit()
    conn.close()
    return True


def rebuild_embeddings(db_path: Path, model_name: str = DEFAULT_MODEL, cache_folder: Optional[Path] = None):
    model = _ensure_model(model_name, cache_folder)
    entries = list_entries(db_path, limit=100000, offset=0, include_deleted=False)
    texts = []
    ids = []
    for e in entries:
        t = " ".join([e.get("word") or "", e.get("translation") or "", e.get("notes") or ""]).strip()
        if not t:
            continue
        texts.append(t)
        ids.append(e["id"])
    if not ids:
        return 0
    embs = _encode(model, texts)
    now = time.time()
    conn = _get_conn(db_path)
    cur = conn.cursor()
    for entry_id, emb in zip(ids, embs):
        buf = _pack_vec([float(x) for x in emb])
        cur.execute(
            """
            INSERT INTO entry_embeddings(entry_id, model, dim, vec, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(entry_id) DO UPDATE SET model=excluded.model, dim=excluded.dim, vec=excluded.vec, updated_at=excluded.updated_at
            """,
            (entry_id, model_name, len(emb), sqlite3.Binary(buf), now),
        )
    conn.commit()
    conn.close()
    return len(ids)


def semantic_search(db_path: Path, q: str, top_k: int = 10, model_name: str = DEFAULT_MODEL, cache_folder: Optional[Path] = None):
    model = _ensure_model(model_name, cache_folder)
    q_emb = _encode(model, [q])[0]
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT entry_id, model, dim, vec FROM entry_embeddings WHERE model = ?",
        (model_name,),
    )
    rows = cur.fetchall()
    conn.close()
    ids = []
    embs = []
    for row in rows:
        entry_id, model_saved, dim, buf = row
        if model_saved != model_name:
            continue
        vec = _unpack_vec(buf)
        if len(vec) != dim:
            continue
        ids.append(entry_id)
        embs.append(vec)
    # ensure embeddings exist
    if not ids:
        rebuild_embeddings(db_path, model_name=model_name, cache_folder=cache_folder)
        return semantic_search(db_path, q, top_k=top_k, model_name=model_name, cache_folder=cache_folder)

    # compute cosine
    try:
        import numpy as np  # type: ignore
    except ImportError as e:
        raise SemanticUnavailable("numpy not installed") from e
    qv = np.array(q_emb, dtype=np.float32)
    m = np.array(embs, dtype=np.float32)
    qnorm = np.linalg.norm(qv)
    mnorm = np.linalg.norm(m, axis=1)
    sims = (m @ qv) / (mnorm * qnorm + 1e-8)
    order = np.argsort(-sims)
    top = []
    for idx in order[:top_k]:
        entry = get_entry(db_path, ids[idx])
        if not entry:
            continue
        top.append(
            {
                "id": ids[idx],
                "language": entry["language"],
                "word": entry["word"],
                "translation": entry.get("translation"),
                "notes": entry.get("notes"),
                "score": float(sims[idx]),
                "match_type": "semantic",
            }
        )
    return top


def semantic_status(db_path: Path, model_name: str = DEFAULT_MODEL, cache_folder: Optional[Path] = None):
    try:
        _ensure_model(model_name, cache_folder)
    except SemanticUnavailable:
        return {"enabled": False, "model": model_name}
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM entry_embeddings WHERE model = ?", (model_name,))
    count = cur.fetchone()[0]
    conn.close()
    return {"enabled": True, "model": model_name, "count": count}
