from pathlib import Path
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

from .exact import resolve_exact
from .fuzzy import resolve_fuzzy
from search import search_like
from semantic import SemanticUnavailable, semantic_search
from ann.index_manager import ann_search


def resolve_entry_candidates(db_path: Path, q: str, language: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
    """
    Resolve a query token into best + candidate list using exact, fuzzy, LIKE, and semantic fallbacks.
    Always returns cross-language matches so Chinese tokens can link to English entries (and vice versa).
    """
    candidates: List[Dict[str, Any]] = []
    seen = set()

    def _push(entry_id: int, lang: str, word: str, score: float, match_type: str):
        if entry_id in seen:
            return
        # prefer requested language slightly when available
        boost = 0.05 if language and lang == language else 0.0
        candidates.append(
            {
                "entry_id": entry_id,
                "word": word,
                "language": lang,
                "score": score + boost,
                "match_type": match_type,
            }
        )
        seen.add(entry_id)

    # 1) Exact in hinted language, then any language
    for c in resolve_exact(db_path, q, language):
        _push(c["entry_id"], c["language"], c["word"], 1.0, c["match_type"])
    if len(candidates) < top_k:
        for c in resolve_exact(db_path, q, None):
            _push(c["entry_id"], c["language"], c["word"], 0.95, c["match_type"])

    # 2) Fuzzy in hinted language, then any language with looser threshold
    if len(candidates) < top_k:
        for c in resolve_fuzzy(db_path, q, language, top_k=top_k * 2, threshold=0.35):
            _push(c["entry_id"], c["language"], c["word"], c.get("score", 0.0), c["match_type"])
            if len(candidates) >= top_k:
                break
    if len(candidates) < top_k:
        for c in resolve_fuzzy(db_path, q, None, top_k=top_k * 3, threshold=0.3):
            _push(c["entry_id"], c["language"], c["word"], c.get("score", 0.0), c["match_type"])
            if len(candidates) >= top_k:
                break

    # 3) LIKE search across word/translation/notes for substring overlap
    if len(candidates) < top_k:
        like_hits = search_like(db_path, q, limit=top_k * 2, offset=0)
        for h in like_hits:
            blob = " ".join([h.get("word") or "", h.get("translation") or ""])
            score = SequenceMatcher(None, q, blob).ratio()
            _push(h["id"], h["language"], h.get("word") or "", score, "like")
            if len(candidates) >= top_k:
                break

    # 4) Semantic / ANN fallback (cross-language capable model)
    if len(candidates) < top_k:
        try:
            try:
                semantic_hits = ann_search(db_path, q, top_k=top_k * 2)
            except SemanticUnavailable:
                semantic_hits = semantic_search(db_path, q, top_k=top_k * 2)
            for s in semantic_hits:
                _push(s["id"], s["language"], s.get("word") or "", s.get("score", 0.0), s.get("match_type", "semantic"))
                if len(candidates) >= top_k:
                    break
        except SemanticUnavailable:
            pass

    candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    best = candidates[0] if candidates else None
    return {"best": best, "candidates": candidates[:top_k]}
