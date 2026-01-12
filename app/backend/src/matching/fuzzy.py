from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3
from difflib import SequenceMatcher


def resolve_fuzzy(db_path: Path, q: str, language: Optional[str] = None, top_k: int = 5, threshold: float = 0.55) -> List[Dict[str, Any]]:
    if not q:
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if language:
        cur.execute(
            """
            SELECT id, language, word, translation
            FROM entries
            WHERE deleted_at IS NULL AND language = ?
            """,
            (language,),
        )
    else:
        cur.execute(
            """
            SELECT id, language, word, translation
            FROM entries
            WHERE deleted_at IS NULL
            """
        )
    rows = cur.fetchall()
    conn.close()

    scored: List[Dict[str, Any]] = []
    for rid, lang, word, trans in rows:
        best_score = 0.0
        match_field = ""
        if word:
            s = SequenceMatcher(None, q, word).ratio()
            if s > best_score:
                best_score = s
                match_field = "word"
        if trans:
            s = SequenceMatcher(None, q, trans).ratio()
            if s > best_score:
                best_score = s
                match_field = "translation"
        if best_score >= threshold:
            scored.append(
                {
                    "entry_id": rid,
                    "word": word,
                    "language": lang,
                    "score": best_score,
                    "match_type": f"fuzzy_{match_field or 'word'}",
                }
            )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
