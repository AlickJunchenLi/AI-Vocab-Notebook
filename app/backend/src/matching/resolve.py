from pathlib import Path
from typing import List, Dict, Any, Optional

from .exact import resolve_exact
from .fuzzy import resolve_fuzzy


def resolve_entry_candidates(db_path: Path, q: str, language: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
    """
    Resolve a query token into best + candidate list using exact then fuzzy.
    """
    candidates: List[Dict[str, Any]] = []
    exact = resolve_exact(db_path, q, language)
    seen = set()
    for c in exact:
        if c["entry_id"] in seen:
            continue
        candidates.append(c)
        seen.add(c["entry_id"])
    if len(candidates) < top_k:
        fuzzy = resolve_fuzzy(db_path, q, language, top_k=top_k, threshold=0.3)
        for c in fuzzy:
            if c["entry_id"] in seen:
                continue
            candidates.append(c)
            seen.add(c["entry_id"])
            if len(candidates) >= top_k:
                break
    best = candidates[0] if candidates else None
    return {"best": best, "candidates": candidates[:top_k]}
