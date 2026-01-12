from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3


def resolve_exact(db_path: Path, q: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Exact match on word or translation (case-insensitive).
    """
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

    q_lower = q.lower()
    results: List[Dict[str, Any]] = []
    for rid, lang, word, trans in rows:
        if word and word.lower() == q_lower:
            results.append({"entry_id": rid, "word": word, "language": lang, "score": 1.0, "match_type": "exact_word"})
        elif trans and trans.lower() == q_lower:
            results.append({"entry_id": rid, "word": word, "language": lang, "score": 0.95, "match_type": "exact_translation"})
    return results
