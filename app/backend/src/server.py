import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from db import (
    init_db,
    add_entry,
    list_entries,
    get_entry,
    update_entry,
    soft_delete_entry,
    upsert_relation,
    list_relations,
    find_translation_matches,
    find_synonym_matches,
    get_entries_by_ids,
    add_record,
    update_record,
    get_record,
    list_records,
    replace_record_links,
    fetch_record_links,
    enqueue_ann_op,
)
from search import search_like, search_fuzzy, search_fts
from matching.tokens import extract_tokens
from matching.resolve import resolve_entry_candidates
from retrieval.graph_first import graph_bfs
from semantic import (
    SemanticUnavailable,
    semantic_search,
    rebuild_embeddings,
    semantic_status,
)
from ann.index_manager import ann_status as ann_status_fn, rebuild_ann_index, ann_search, apply_ann_updates


def write_response(res: Dict[str, Any]):
    sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def ok(id_val: Any, data: Any):
    return {"id": id_val, "ok": True, "data": data}


def err(id_val: Any, code: str, message: str):
    return {"id": id_val, "ok": False, "error": {"code": code, "message": message}}


def handle_ping(_db: Path, payload: Dict[str, Any]):
    return "pong"


def handle_add_entry(db_path: Path, payload: Dict[str, Any]):
    lang = payload.get("language")
    word = payload.get("word")
    translation = payload.get("translation", "")
    notes = payload.get("notes", "")
    if not lang or not word:
        raise ValueError("missing_fields")
    row_id = add_entry(db_path, lang, word, translation, notes)
    enqueue_ann_op(db_path, row_id, "upsert", "add_entry")
    # auto-link to existing entries
    auto_relations = []
    # link translations
    targets = find_translation_matches(db_path, lang, translation)
    for tid in targets:
        try:
            rel_id = upsert_relation(db_path, row_id, tid, "translation")
            auto_relations.append(rel_id)
        except Exception:
            continue
    # link synonyms
    syn_targets = find_synonym_matches(db_path, lang, word)
    for tid in syn_targets:
        if tid == row_id:
            continue
        try:
            rel_id = upsert_relation(db_path, row_id, tid, "synonym")
            auto_relations.append(rel_id)
        except Exception:
            continue
    return {"id": row_id, "linked_relations": auto_relations}


def handle_get_entry(db_path: Path, payload: Dict[str, Any]):
    entry_id = payload.get("id")
    if not entry_id:
        raise ValueError("missing_fields")
    entry = get_entry(db_path, entry_id)
    if entry is None:
        raise LookupError("not_found")
    return entry


def handle_update_entry(db_path: Path, payload: Dict[str, Any]):
    entry_id = payload.get("id")
    if not entry_id:
        raise ValueError("missing_fields")
    lang = payload.get("language")
    word = payload.get("word")
    translation = payload.get("translation", "")
    notes = payload.get("notes", "")
    if not lang or not word:
        raise ValueError("missing_fields")
    changed = update_entry(db_path, entry_id, lang, word, translation, notes)
    enqueue_ann_op(db_path, entry_id, "upsert", "update_entry")
    return {"updated": changed}


def handle_delete_entry(db_path: Path, payload: Dict[str, Any]):
    entry_id = payload.get("id")
    if not entry_id:
        raise ValueError("missing_fields")
    changed = soft_delete_entry(db_path, entry_id)
    enqueue_ann_op(db_path, entry_id, "delete", "delete_entry")
    return {"deleted": changed}


def handle_list_entries(db_path: Path, payload: Dict[str, Any]):
    limit = int(payload.get("limit", 50))
    offset = int(payload.get("offset", 0))
    include_deleted = bool(payload.get("include_deleted", False))
    entries = list_entries(db_path, limit=limit, offset=offset, include_deleted=include_deleted)
    return entries


def handle_upsert_relation(db_path: Path, payload: Dict[str, Any]):
    from_id = payload.get("from_id")
    to_id = payload.get("to_id")
    rel_type = payload.get("type")
    if not from_id or not to_id or not rel_type:
        raise ValueError("missing_fields")
    rel_id = upsert_relation(db_path, from_id, to_id, rel_type)
    return {"id": rel_id}


def handle_list_relations(db_path: Path, payload: Dict[str, Any]):
    entry_id = payload.get("id")
    if not entry_id:
        raise ValueError("missing_fields")
    rels = list_relations(db_path, entry_id)
    return rels


def handle_search_entries(db_path: Path, payload: Dict[str, Any]):
    q = payload.get("q", "")
    mode = payload.get("mode", "like")
    limit = int(payload.get("limit", 50))
    offset = int(payload.get("offset", 0))
    expand = bool(payload.get("expand_relations", False))
    fallback_fuzzy = bool(payload.get("fallback_fuzzy", True))
    if not q:
        return []
    results = []
    if mode == "fuzzy":
        results = search_fuzzy(db_path, q, limit, offset)
    elif mode == "fts":
        results = search_fts(db_path, q, limit, offset)
        if not results and fallback_fuzzy:
            results = search_fuzzy(db_path, q, limit, offset)
    elif mode == "semantic":
        try:
            # prefer ANN if available
            try:
                results = ann_search(db_path, q, top_k=limit)
            except SemanticUnavailable:
                results = semantic_search(db_path, q, top_k=limit)
        except SemanticUnavailable as se:
            raise se
    else:
        results = search_like(db_path, q, limit, offset)
        if not results and fallback_fuzzy:
            results = search_fuzzy(db_path, q, limit, offset)

    if expand and results:
        ids = [r["id"] for r in results]
        related_ids = set(ids)
        for eid in ids:
            rels = list_relations(db_path, eid)
            for r in rels:
                related_ids.add(r["from_id"])
                related_ids.add(r["to_id"])
        extra_ids = [i for i in related_ids if i not in ids]
        neighbors = get_entries_by_ids(db_path, extra_ids)
        results = results + neighbors
    return results


def _build_annotations(db_path: Path, text: str) -> Dict[str, Any]:
    tokens = extract_tokens(text)
    annotations = []
    links_to_store = []
    for t in tokens:
        resolved = resolve_entry_candidates(db_path, t["surface"], t.get("kind"))
        best = resolved.get("best")
        ann = {
            "start": t["start"],
            "end": t["end"],
            "surface": t["surface"],
            "entry_id": best["entry_id"] if best else None,
            "score": best["score"] if best else None,
            "match_type": best["match_type"] if best else None,
            "candidates": resolved.get("candidates", []),
        }
        annotations.append(ann)
        if best:
            links_to_store.append(
                {
                    "entry_id": best["entry_id"],
                    "start": t["start"],
                    "end": t["end"],
                    "surface": t["surface"],
                    "match_type": best["match_type"],
                    "score": best["score"],
                }
            )
    return {"annotations": annotations, "links": links_to_store}


def _build_annotations_from_links(text: str, links: List[Dict[str, Any]]):
    tokens = extract_tokens(text)
    link_map = {(l["start"], l["end"]): l for l in links}
    annotations = []
    for t in tokens:
        l = link_map.get((t["start"], t["end"]))
        annotations.append(
            {
                "start": t["start"],
                "end": t["end"],
                "surface": t["surface"],
                "entry_id": l["entry_id"] if l else None,
                "score": l["score"] if l else None,
                "match_type": l["match_type"] if l else None,
                "candidates": [],
            }
        )
    return annotations


def _get_record_with_annotations(db_path: Path, rid: int) -> Dict[str, Any]:
    rec = get_record(db_path, rid)
    if not rec:
        return None
    links = fetch_record_links(db_path, rid)
    rec["annotations"] = _build_annotations_from_links(rec["text"], links)
    return rec


def handle_add_record(db_path: Path, payload: Dict[str, Any]):
    init_db(db_path)
    text = payload.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("missing_fields")
    rid = add_record(db_path, text)
    built = _build_annotations(db_path, text)
    replace_record_links(db_path, rid, built["links"])
    return {"record_id": rid, "annotations": built["annotations"]}


def handle_update_record(db_path: Path, payload: Dict[str, Any]):
    rid = payload.get("record_id")
    text = payload.get("text", "")
    if not rid or not isinstance(text, str) or not text.strip():
        raise ValueError("missing_fields")
    ok = update_record(db_path, rid, text)
    if not ok:
        raise LookupError("not_found")
    built = _build_annotations(db_path, text)
    replace_record_links(db_path, rid, built["links"])
    return {"record_id": rid, "annotations": built["annotations"]}


def handle_get_record(db_path: Path, payload: Dict[str, Any]):
    rid = payload.get("record_id")
    if not rid:
        raise ValueError("missing_fields")
    rec = _get_record_with_annotations(db_path, rid)
    if not rec:
        raise LookupError("not_found")
    return rec


def handle_list_records(db_path: Path, payload: Dict[str, Any]):
    limit = int(payload.get("limit", 50))
    offset = int(payload.get("offset", 0))
    return list_records(db_path, limit=limit, offset=offset)


def handle_link_record(db_path: Path, payload: Dict[str, Any]):
    rid = payload.get("record_id")
    entry_id = payload.get("entry_id")
    start = payload.get("start")
    end = payload.get("end")
    surface = payload.get("surface", "")
    match_type = payload.get("match_type", "manual")
    score = float(payload.get("score", 1.0))
    if rid is None or entry_id is None or start is None or end is None:
        raise ValueError("missing_fields")
    rec = get_record(db_path, rid)
    if not rec:
        raise LookupError("not_found")
    text = rec["text"]
    if start < 0 or end > len(text) or start >= end:
        raise ValueError("bad_range")
    replace_record_links(
        db_path,
        rid,
        # replace existing link on same span
        [
            l
            for l in fetch_record_links(db_path, rid)
            if not (l["start"] == start and l["end"] == end)
        ]
        + [
            {
                "entry_id": entry_id,
                "start": start,
                "end": end,
                "surface": surface or text[start:end],
                "match_type": match_type,
                "score": score,
            }
        ],
    )
    rec_with_ann = _get_record_with_annotations(db_path, rid)
    return {"ok": True, "annotations": rec_with_ann["annotations"] if rec_with_ann else []}


def handle_unlink_record(db_path: Path, payload: Dict[str, Any]):
    rid = payload.get("record_id")
    entry_id = payload.get("entry_id")
    start = payload.get("start")
    end = payload.get("end")
    if rid is None or entry_id is None or start is None or end is None:
        raise ValueError("missing_fields")
    links = fetch_record_links(db_path, rid)
    remaining = [l for l in links if not (l["entry_id"] == entry_id and l["start"] == start and l["end"] == end)]
    replace_record_links(
        db_path,
        rid,
        remaining,
    )
    rec_with_ann = _get_record_with_annotations(db_path, rid)
    return {"ok": True, "annotations": rec_with_ann["annotations"] if rec_with_ann else []}


def handle_resolve_entry(db_path: Path, payload: Dict[str, Any]):
    q = payload.get("q", "")
    language = payload.get("language")
    topk = int(payload.get("topK", 5))
    if not q:
        raise ValueError("missing_fields")
    resolved = resolve_entry_candidates(db_path, q, language, top_k=topk)
    return resolved


def handle_get_synonyms(db_path: Path, payload: Dict[str, Any]):
    q = payload.get("q", "")
    language = payload.get("language")
    depth = int(payload.get("depth", 2))
    topk = int(payload.get("topK", 20))
    fallback = bool(payload.get("fallback", True))
    include_types = payload.get("includeTypes") or ["synonym", "translation"]
    if not q:
        raise ValueError("missing_fields")
    resolved = resolve_entry_candidates(db_path, q, language, top_k=max(5, topk))
    best = resolved.get("best")
    if not best:
        return {"entry": None, "graph_results": [], "fallback_results": [], "candidates": resolved.get("candidates", [])}

    start_entry = get_entry(db_path, best["entry_id"])
    graph_results = graph_bfs(db_path, best["entry_id"], depth=depth, include_types=include_types)
    visited_ids = set([best["entry_id"]] + [g["entry_id"] for g in graph_results])

    fallback_results = []
    if fallback and len(graph_results) < topk:
        # reuse candidates + search_like as supplement
        candidates = resolved.get("candidates", [])
        for c in candidates:
            if c["entry_id"] not in visited_ids:
                fallback_results.append(
                    {
                        "entry_id": c["entry_id"],
                        "word": c["word"],
                        "language": c["language"],
                        "score": c.get("score"),
                        "match_type": c.get("match_type", "candidate"),
                    }
                )
                visited_ids.add(c["entry_id"])
                if len(graph_results) + len(fallback_results) >= topk:
                    break
        if len(graph_results) + len(fallback_results) < topk:
            extra = search_like(db_path, q, limit=topk * 2, offset=0)
            for e in extra:
                if e["id"] in visited_ids:
                    continue
                fallback_results.append(
                    {
                        "entry_id": e["id"],
                        "word": e["word"],
                        "language": e["language"],
                        "score": None,
                        "match_type": "like",
                    }
                )
                visited_ids.add(e["id"])
                if len(graph_results) + len(fallback_results) >= topk:
                    break

    return {
        "entry": {"entry_id": best["entry_id"], "word": start_entry["word"], "language": start_entry["language"]} if start_entry else None,
        "graph_results": graph_results[:topk],
        "fallback_results": fallback_results[: max(0, topk - len(graph_results))],
        "candidates": resolved.get("candidates", []),
    }


def handle_semantic_status(db_path: Path, payload: Dict[str, Any]):
    model = payload.get("model") or semantic.DEFAULT_MODEL
    return semantic_status(db_path, model_name=model)


def handle_rebuild_embeddings(db_path: Path, payload: Dict[str, Any]):
    model = payload.get("model") or semantic.DEFAULT_MODEL
    count = rebuild_embeddings(db_path, model_name=model)
    return {"rebuilt": count}


def handle_ann_status(db_path: Path, payload: Dict[str, Any]):
    model = payload.get("model") or semantic.DEFAULT_MODEL
    return ann_status_fn(db_path, model)


def handle_rebuild_ann_index(db_path: Path, payload: Dict[str, Any]):
    model = payload.get("model") or semantic.DEFAULT_MODEL
    count = rebuild_ann_index(db_path, model)
    return {"rebuilt": count}


def handle_ann_apply_updates(db_path: Path, payload: Dict[str, Any]):
    model = payload.get("model") or semantic.DEFAULT_MODEL
    res = apply_ann_updates(db_path, model=model)
    return res


HANDLERS = {
    "ping": handle_ping,
    "add_entry": handle_add_entry,
    "get_entry": handle_get_entry,
    "update_entry": handle_update_entry,
    "delete_entry": handle_delete_entry,
    "list_entries": handle_list_entries,
    "upsert_relation": handle_upsert_relation,
    "list_relations": handle_list_relations,
    "search_entries": handle_search_entries,
    "add_record": handle_add_record,
    "update_record": handle_update_record,
    "get_record": handle_get_record,
    "list_records": handle_list_records,
    "link_record": handle_link_record,
    "unlink_record": handle_unlink_record,
    "resolve_entry": handle_resolve_entry,
    "get_synonyms": handle_get_synonyms,
    "semantic_status": handle_semantic_status,
    "rebuild_embeddings": handle_rebuild_embeddings,
    "ann_status": handle_ann_status,
    "rebuild_ann_index": handle_rebuild_ann_index,
    "ann_apply_updates": handle_ann_apply_updates,
}


def main():
    if len(sys.argv) < 2:
        write_response(err(None, "missing_db", "missing db path arg"))
        return
    db_path = Path(sys.argv[1])
    init_db(db_path)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            write_response(err(None, "invalid_json", "cannot parse line"))
            continue

        cmd = msg.get("cmd")
        req_id = msg.get("id")
        payload = msg.get("payload") or {}
        handler = HANDLERS.get(cmd or "")
        if not handler:
            write_response(err(req_id, "unknown_cmd", f"unknown cmd {cmd}"))
            continue
        try:
            data = handler(db_path, payload)
            write_response(ok(req_id, data))
        except ValueError as ve:
            if str(ve) == "missing_fields":
                write_response(err(req_id, "missing_fields", "required fields missing or empty"))
            elif str(ve) == "bad_range":
                write_response(err(req_id, "bad_range", "invalid start/end range"))
            else:
                write_response(err(req_id, "bad_request", str(ve)))
        except SemanticUnavailable as se:
            write_response(err(req_id, "SEMANTIC_DISABLED", str(se)))
        except LookupError:
            write_response(err(req_id, "not_found", "entry not found"))
        except Exception as exc:  # noqa: BLE001
            write_response(err(req_id, "exception", str(exc)))


if __name__ == "__main__":
    main()
