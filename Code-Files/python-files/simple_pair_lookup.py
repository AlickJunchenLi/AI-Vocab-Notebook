# -*- coding: utf-8 -*-
"""Check if two terms are linked as synonyms/translations in the built DB.

Example:
  python Code-Files/python-files/simple_pair_lookup.py --db notebook.db --w1 "happy" --w2 "glad" --language en
  python Code-Files/python-files/simple_pair_lookup.py --db notebook.db --w1 "happy" --w2 "快乐" --language zh

Returns true/false and any stored score from synonym_edge/translation_edge.
"""
import argparse
import sqlite3
from pathlib import Path
from typing import Optional, Tuple


def normalize(term: str, language: str) -> str:
    term = term.strip()
    if language == "en":
        term = term.lower()
    return term


def lookup_synonym(conn: sqlite3.Connection, a: str, b: str, language: str) -> Optional[float]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT score FROM synonym_edge
        WHERE language = ? AND (
            (left_term = ? AND right_term = ?) OR
            (left_term = ? AND right_term = ?)
        )
        LIMIT 1
        """,
        (language, a, b, b, a),
    )
    row = cur.fetchone()
    return row[0] if row else None


def lookup_translation(conn: sqlite3.Connection, a: str, b: str) -> Optional[float]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT score FROM translation_edge
        WHERE (en_term = ? AND zh_term = ?) OR (en_term = ? AND zh_term = ?)
        LIMIT 1
        """,
        (a, b, b, a),
    )
    row = cur.fetchone()
    return row[0] if row else None


def check_pair(db_path: Path, w1: str, w2: str, language: str) -> Tuple[bool, Optional[float], str]:
    w1n = normalize(w1, language)
    w2n = normalize(w2, language)
    conn = sqlite3.connect(db_path)
    score = lookup_synonym(conn, w1n, w2n, language)
    if score is not None:
        conn.close()
        return True, score, "synonym_edge"
    # cross-language if terms look different language
    cross_score = lookup_translation(conn, w1n, w2n)
    conn.close()
    if cross_score is not None:
        return True, cross_score, "translation_edge"
    return False, None, "none"


def main():
    parser = argparse.ArgumentParser(description="Check if two terms are linked in the DB")
    parser.add_argument("--db", default="notebook.db", help="SQLite path from ai_initializer build")
    parser.add_argument("--w1", required=True, help="First word")
    parser.add_argument("--w2", required=True, help="Second word")
    parser.add_argument("--language", choices=["en", "zh"], default="en", help="Language of the pair (for synonym lookup)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found at {db_path}. Build it first (test_interface.py --build).")

    linked, score, source = check_pair(db_path, args.w1, args.w2, args.language)
    print(f"linked={linked}")
    print(f"source={source}")
    if score is not None:
        print(f"score={score:.3f}")


if __name__ == "__main__":
<<<<<<< HEAD
    main()
=======
    main()
>>>>>>> 792df40 (lasdfsa)
