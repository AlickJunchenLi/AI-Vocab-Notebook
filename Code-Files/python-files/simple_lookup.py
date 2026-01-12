# -*- coding: utf-8 -*-
"""Simple true/false + synonym lookup for English/Chinese terms.

Examples:
  python Code-Files/python-files/simple_lookup.py --db notebook.db --text "happy" --language en
  python Code-Files/python-files/simple_lookup.py --db notebook.db --text "hao" --language zh

Returns whether the term exists in the edges DB and lists direct synonyms (and translations).
"""
import argparse
import sqlite3
from pathlib import Path
from typing import List, Set, Tuple


def normalize(term: str, language: str) -> str:
    term = term.strip()
    if language == "en":
        term = term.lower()
    return term


def fetch_synonyms(conn: sqlite3.Connection, term: str, language: str) -> Set[str]:
    cur = conn.cursor()
    peers: Set[str] = set()
    cur.execute(
        """
        SELECT left_term, right_term FROM synonym_edge
        WHERE language = ? AND (left_term = ? OR right_term = ?)
        """,
        (language, term, term),
    )
    for left, right in cur.fetchall():
        if left == term and right:
            peers.add(right)
        elif right == term and left:
            peers.add(left)
    return peers


def fetch_translations(conn: sqlite3.Connection, term: str, language: str) -> Set[str]:
    cur = conn.cursor()
    peers: Set[str] = set()
    if language == "en":
        cur.execute("SELECT zh_term FROM translation_edge WHERE en_term = ?", (term,))
        peers.update(t for (t,) in cur.fetchall() if t)
    else:
        cur.execute("SELECT en_term FROM translation_edge WHERE zh_term = ?", (term,))
        peers.update(t for (t,) in cur.fetchall() if t)
    return peers


def lookup(db_path: Path, raw_term: str, language: str) -> Tuple[bool, List[str], List[str]]:
    term = normalize(raw_term, language)
    conn = sqlite3.connect(db_path)
    synonyms = fetch_synonyms(conn, term, language)
    translations = fetch_translations(conn, term, language)
    conn.close()
    found = bool(synonyms or translations)
    return found, sorted(synonyms), sorted(translations)


def main():
    parser = argparse.ArgumentParser(description="Simple synonym/translation lookup")
    parser.add_argument("--db", default="notebook.db", help="SQLite path produced by ai_initializer build")
    parser.add_argument("--text", required=True, help="Input word/phrase")
    parser.add_argument("--language", choices=["en", "zh"], default="en", help="Language of the input")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found at {db_path}. Run ai_initializer/test_interface with --build first.")

    found, synonyms, translations = lookup(db_path, args.text, args.language)
    print(f"found={found}")
    if synonyms:
        print("synonyms:")
        for s in synonyms:
            print(f"  {s}")
    if translations:
        print("translations:")
        for t in translations:
            print(f"  {t}")


if __name__ == "__main__":
    main()
