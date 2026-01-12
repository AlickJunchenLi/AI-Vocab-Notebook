from typing import List, Dict, Any, Set, Tuple
from db import list_relations, get_entry


def graph_bfs(db_path, start_id: int, depth: int = 2, include_types: List[str] = None) -> List[Dict[str, Any]]:
    """
    BFS over relations starting from start_id.
    Returns list of {entry_id, distance, via_type}.
    """
    if include_types is None:
        include_types = ["synonym", "translation"]
    include_set = set(include_types)

    visited: Set[int] = set([start_id])
    queue: List[Tuple[int, int, str]] = [(start_id, 0, "")]
    results: List[Dict[str, Any]] = []

    while queue:
        current, dist, via = queue.pop(0)
        if dist >= depth:
            continue
        rels = list_relations(db_path, current)
        for r in rels:
            if r["type"] not in include_set:
                continue
            neighbor = r["to_id"] if r["from_id"] == current else r["from_id"]
            if neighbor in visited:
                continue
            visited.add(neighbor)
            next_dist = dist + 1
            queue.append((neighbor, next_dist, r["type"]))
            entry = get_entry(db_path, neighbor)
            if entry:
                results.append(
                    {
                        "entry_id": neighbor,
                        "language": entry["language"],
                        "word": entry["word"],
                        "translation": entry.get("translation"),
                        "distance": next_dist,
                        "via": r["type"],
                    }
                )
    # sort by distance then word
    results.sort(key=lambda x: (x["distance"], x["word"]))
    return results
