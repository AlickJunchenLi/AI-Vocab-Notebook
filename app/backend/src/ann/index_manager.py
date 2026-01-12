import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from array import array

from db import get_entry
from semantic import (
    DEFAULT_MODEL,
    SemanticUnavailable,
    _ensure_model,
    _encode,
    _unpack_vec,
)
from ann.faiss_backend import FaissBackend, AnnUnavailable
from db import fetch_ann_queue, clear_ann_queue, count_ann_queue


def _load_embeddings(db_path: Path, model: str):
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ee.entry_id, ee.dim, ee.vec
        FROM entry_embeddings ee
        JOIN entries e ON e.id = ee.entry_id
        WHERE ee.model = ? AND e.deleted_at IS NULL
        """,
        (model,),
    )
    rows = cur.fetchall()
    conn.close()
    ids = []
    vecs = []
    dim = None
    for rid, rdim, rvec in rows:
        ids.append(rid)
        dim = rdim
        vecs.append(_unpack_vec(rvec))
    return ids, vecs, dim


def _paths(db_path: Path, model: str):
    base = db_path.parent / "ann"
    safe_model = model.replace("/", "_").replace(":", "_")
    index_path = base / f"semantic_{safe_model}.faiss"
    meta_path = base / f"semantic_{safe_model}.json"
    return base, index_path, meta_path


def ann_status(db_path: Path, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    try:
        FaissBackend(1)
    except AnnUnavailable:
        return {"enabled": False, "backend": "faiss", "pending": count_ann_queue(db_path)}

    base, index_path, meta_path = _paths(db_path, model)
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    return {
        "enabled": True,
        "backend": "faiss",
        "model": model,
        "index_path": str(index_path),
        "meta": meta,
        "exists": index_path.exists(),
        "pending": count_ann_queue(db_path),
    }


def rebuild_ann_index(db_path: Path, model: str = DEFAULT_MODEL) -> int:
    # ensure faiss
    try:
        dummy = FaissBackend(1)
    except AnnUnavailable as e:
        raise SemanticUnavailable(str(e))
    ids, vecs, dim = _load_embeddings(db_path, model)
    if not ids or not vecs or dim is None:
        return 0
    base, index_path, meta_path = _paths(db_path, model)
    base.mkdir(parents=True, exist_ok=True)
    backend = FaissBackend(dim)
    index = backend.build(vecs, ids)
    backend.save(index, str(index_path))
    meta = {"model": model, "dim": dim, "count": len(ids), "last_built": time.time()}
    meta_path.write_text(json.dumps(meta))
    return len(ids)


def apply_ann_updates(db_path: Path, model: str = DEFAULT_MODEL, max_n: int = 200) -> Dict[str, Any]:
    queue = fetch_ann_queue(db_path, max_n=max_n)
    if not queue:
        return {"applied": 0, "rebuilt": 0}
    # For simplicity with faiss: rebuild full index after applying queue
    # Ensure embeddings exist for all upsert entries
    # Collect upsert ids
    upsert_ids = [q["entry_id"] for q in queue if q["op"] == "upsert"]
    try:
        for eid in upsert_ids:
            ensure_embedding_for_entry(db_path, eid, model_name=model)
        rebuilt = rebuild_ann_index(db_path, model)
    finally:
        clear_ann_queue(db_path, [q["id"] for q in queue])
    return {"applied": len(queue), "rebuilt": rebuilt}


def ann_search(db_path: Path, q: str, top_k: int = 10, model: str = DEFAULT_MODEL):
    # encode query
    model_obj = _ensure_model(model, None)
    q_emb = _encode(model_obj, [q])[0]
    status = ann_status(db_path, model)
    if not status.get("enabled"):
        raise SemanticUnavailable("ANN backend not available")
    base, index_path, meta_path = _paths(db_path, model)
    if not index_path.exists():
        # try rebuild
        cnt = rebuild_ann_index(db_path, model)
        if cnt == 0:
            raise SemanticUnavailable("No embeddings to build ANN")
    try:
        backend = FaissBackend(len(q_emb))
    except AnnUnavailable as e:
        raise SemanticUnavailable(str(e))
    index = backend.load(str(index_path))
    hits = backend.search(index, q_emb, top_k)
    results = []
    for eid, score in hits:
        entry = get_entry(db_path, eid)
        if not entry or entry.get("deleted_at"):
            continue
        results.append(
            {
                "id": eid,
                "language": entry["language"],
                "word": entry["word"],
                "translation": entry.get("translation"),
                "notes": entry.get("notes"),
                "score": score,
                "match_type": "semantic_ann",
            }
        )
    return results
