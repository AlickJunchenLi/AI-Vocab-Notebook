from pathlib import Path
from typing import List, Dict, Any, Tuple
import sqlite3
from difflib import SequenceMatcher


def _to_row_dict(row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {
        "id": row[0],
        "language": row[1],
        "word": row[2],
        "translation": row[3],
        "notes": row[4],
        "updated_at": row[5],
    }


def search_like(db_path: Path, q: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    pattern = f"%{q}%"
    cur.execute(
        """
        SELECT id, language, word, translation, notes, updated_at
        FROM entries
        WHERE deleted_at IS NULL AND (word LIKE ? OR translation LIKE ? OR notes LIKE ?)
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (pattern, pattern, pattern, limit, offset),
    )
    rows = cur.fetchall()
    conn.close()
    return [_to_row_dict(r) for r in rows]


def search_fuzzy(db_path: Path, q: str, limit: int, offset: int, threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Lightweight fuzzy search over word/translation/notes using SequenceMatcher.
    Returns entries sorted by best match score.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, language, word, translation, notes, updated_at
        FROM entries
        WHERE deleted_at IS NULL
        """
    )
    rows = cur.fetchall()
    conn.close()

    scored: List[Tuple[float, Tuple[Any, ...]]] = []
    for r in rows:
        text_blob = " ".join([r[2] or "", r[3] or "", r[4] or ""])
        score = SequenceMatcher(None, q, text_blob).ratio()
        if score >= threshold:
            scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    sliced = scored[offset : offset + limit]
    return [_to_row_dict(r) for _, r in sliced]


def search_fts(db_path: Path, q: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.id, e.language, e.word, e.translation, e.notes,
               bm25(entries_fts) as score,
               snippet(entries_fts, 0, '[', ']', '...', 10) as snippet_word,
               snippet(entries_fts, 1, '[', ']', '...', 10) as snippet_translation,
               snippet(entries_fts, 2, '[', ']', '...', 10) as snippet_notes
        FROM entries_fts
        JOIN entries e ON e.id = entries_fts.rowid
        WHERE e.deleted_at IS NULL AND entries_fts MATCH ?
        ORDER BY score ASC
        LIMIT ? OFFSET ?
        """,
        (q, limit, offset),
    )
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append(
            {
                "id": r[0],
                "language": r[1],
                "word": r[2],
                "translation": r[3],
                "notes": r[4],
                "score": 1.0 / (1.0 + (r[5] if r[5] is not None else 0.0)),
                "snippet": r[6] or r[7] or r[8],
                "match_type": "fts",
            }
        )
    return results
