"""
Main CLI for recording and searching bilingual vocabulary against the notebook DB.

Capabilities:
- Initialize/load the SQLite DB (optionally from a .sql seed).
- Record a user vocab entry with optional meanings.
- Link new bilingual pairs into the shared translation_edge/terms tables.
- Search user entries and (optionally) the base graph in both languages.
"""
import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import torch
from sentence_transformers import SentenceTransformer, util

from ai_initializer import CJK_RE, MODEL_NAME, ensure_tables, query_from_db


USER_SOURCE = "user"


@dataclass
class UserEntry:
    id: int
    en_term: str
    zh_term: str
    meaning_en: str
    meaning_zh: str


def detect_language(text: str) -> str:
    return "zh" if CJK_RE.search(text) else "en"


def normalize(term: str, language: str) -> str:
    term = term.strip()
    if language == "en":
        term = term.lower()
    return term


def ensure_user_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_vocab(
            id INTEGER PRIMARY KEY,
            en_term TEXT,
            zh_term TEXT,
            meaning_en TEXT,
            meaning_zh TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_vocab_en ON user_vocab(en_term)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_vocab_zh ON user_vocab(zh_term)")
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_user_vocab_updated
        AFTER UPDATE ON user_vocab
        FOR EACH ROW
        BEGIN
            UPDATE user_vocab SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        """
    )
    conn.commit()


def seed_from_sql(conn: sqlite3.Connection, sql_path: Path):
    sql_text = sql_path.read_text(encoding="utf-8")
    conn.executescript(sql_text)
    conn.commit()


def ensure_db(db_path: Path, sql_seed: Optional[Path]):
    first_time = not db_path.exists()
    conn = sqlite3.connect(db_path)
    if sql_seed and first_time:
        seed_from_sql(conn, sql_seed)
    ensure_tables(conn)
    ensure_user_tables(conn)
    conn.close()


def upsert_terms(conn: sqlite3.Connection, terms: Iterable[str]):
    rows = []
    for term in terms:
        if not term:
            continue
        lang = "zh" if CJK_RE.search(term) else "en"
        rows.append((normalize(term, lang), lang))
    if not rows:
        return
    cur = conn.cursor()
    cur.executemany("INSERT OR IGNORE INTO terms(term, language) VALUES (?, ?)", rows)
    conn.commit()


def attach_translation(conn: sqlite3.Connection, en_term: Optional[str], zh_term: Optional[str], score: float = 1.0):
    if not en_term or not zh_term:
        return
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO translation_edge(en_term, zh_term, score, source)
        VALUES (?, ?, ?, ?)
        """,
        (normalize(en_term, "en"), normalize(zh_term, "zh"), score, USER_SOURCE),
    )
    conn.commit()


def add_entry(db_path: Path, en_term: Optional[str], zh_term: Optional[str], meaning_en: Optional[str], meaning_zh: Optional[str]) -> int:
    if not en_term and not zh_term:
        raise ValueError("Provide at least one of --en or --zh")
    conn = sqlite3.connect(db_path)
    ensure_tables(conn)
    ensure_user_tables(conn)

    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_vocab(en_term, zh_term, meaning_en, meaning_zh, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (en_term or "", zh_term or "", meaning_en or "", meaning_zh or "", now, now),
    )
    row_id = cur.lastrowid
    upsert_terms(conn, [en_term, zh_term])
    attach_translation(conn, en_term, zh_term)
    conn.close()
    return row_id


def load_user_entries(conn: sqlite3.Connection) -> List[UserEntry]:
    cur = conn.cursor()
    cur.execute("SELECT id, en_term, zh_term, meaning_en, meaning_zh FROM user_vocab")
    rows = cur.fetchall()
    return [UserEntry(*row) for row in rows]


def build_user_text(entry: UserEntry) -> str:
    parts = []
    for field in [entry.en_term, entry.zh_term, entry.meaning_en, entry.meaning_zh]:
        if field:
            parts.append(field.strip())
    return " | ".join(parts)


def search_user_entries(db_path: Path, query_text: str, topk: int, model: SentenceTransformer) -> List[dict]:
    conn = sqlite3.connect(db_path)
    ensure_user_tables(conn)
    entries = load_user_entries(conn)
    conn.close()
    if not entries:
        return []
    texts = [build_user_text(e) for e in entries]
    query_vec = model.encode([query_text], convert_to_tensor=True, normalize_embeddings=True)
    entry_vecs = model.encode(texts, convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_vec, entry_vecs)[0]
    k = min(topk, scores.shape[0])
    values, indices = torch.topk(scores, k)
    results = []
    for val, idx in zip(values.tolist(), indices.tolist()):
        entry = entries[idx]
        results.append(
            {
                "source": "user",
                "score": float(val),
                "en_term": entry.en_term,
                "zh_term": entry.zh_term,
                "meaning_en": entry.meaning_en,
                "meaning_zh": entry.meaning_zh,
            }
        )
    return results


def search_base(db_path: Path, text: str, language: str, topk: int) -> List[dict]:
    hits = query_from_db(db_path, text, language, topk)
    return [{"source": f"base-{language}", "score": score, "term": term} for term, score in hits]


def run_search(db_path: Path, text: str, language: str, topk: int, include_base: bool) -> List[dict]:
    model = SentenceTransformer(MODEL_NAME)
    results = search_user_entries(db_path, text, topk, model)

    lang = language
    if language == "auto":
        lang = detect_language(text)
    if language == "both":
        langs = ["en", "zh"]
    else:
        langs = [lang]

    if include_base:
        for l in langs:
            results.extend(search_base(db_path, text, l, topk))

    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    return results[:topk]


def list_user_entries(db_path: Path, limit: int):
    conn = sqlite3.connect(db_path)
    ensure_user_tables(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, en_term, zh_term, meaning_en, meaning_zh, created_at, updated_at
        FROM user_vocab
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        print(f"#{row[0]} en='{row[1]}' zh='{row[2]}' created={row[5]} updated={row[6]}")
        if row[3]:
            print(f"  meaning_en: {row[3]}")
        if row[4]:
            print(f"  meaning_zh: {row[4]}")


def main():
    parser = argparse.ArgumentParser(description="Bilingual vocab recorder/searcher")
    parser.add_argument("--db", default="notebook.db", help="SQLite DB path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize DB, optionally from SQL seed")
    p_init.add_argument("--sql", type=Path, help="Optional .sql file to load into the DB when creating it")

    p_add = sub.add_parser("add", help="Add a vocab entry and link it into the DB")
    p_add.add_argument("--en", help="English term")
    p_add.add_argument("--zh", help="Chinese term")
    p_add.add_argument("--meaning-en", help="Meaning in English")
    p_add.add_argument("--meaning-zh", help="Meaning in Chinese")

    p_search = sub.add_parser("search", help="Search user vocab (and optionally base DB)")
    p_search.add_argument("--text", required=True, help="Query text")
    p_search.add_argument("--language", choices=["en", "zh", "both", "auto"], default="auto", help="Language hint")
    p_search.add_argument("--topk", type=int, default=10, help="Number of results to return")
    p_search.add_argument("--include-base", action="store_true", help="Also search the base DB tables")

    p_list = sub.add_parser("list", help="List recent user entries")
    p_list.add_argument("--limit", type=int, default=10, help="Rows to show")

    args = parser.parse_args()
    db_path = Path(args.db)

    if args.cmd == "init":
        ensure_db(db_path, args.sql)
        print(f"DB ready at {db_path}")
        return

    if args.cmd == "add":
        row_id = add_entry(db_path, args.en, args.zh, args.meaning_en, args.meaning_zh)
        print(f"Inserted entry #{row_id}")
        return

    if args.cmd == "search":
        results = run_search(db_path, args.text, args.language, args.topk, args.include_base)
        for hit in results:
            if hit["source"] == "user":
                print(f"{hit['score']:.3f}\tUSER\t{hit.get('en_term','')}\t{hit.get('zh_term','')}")
            else:
                print(f"{hit['score']:.3f}\t{hit['source']}\t{hit.get('term','')}")
        return

    if args.cmd == "list":
        list_user_entries(db_path, args.limit)
        return


if __name__ == "__main__":
    main()
