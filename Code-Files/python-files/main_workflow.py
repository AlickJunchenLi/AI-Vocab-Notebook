# -*- coding: utf-8 -*-
"""
Bilingual vocab notebook main workflow.

Provides a single CLI that can:
- Load an existing SQLite DB (or build it from a SQL dump).
- Record new English/Chinese vocab pairs with optional meanings.
- Link new entries into the existing synonym/translation tables.
- Search a user's recorded vocab bilingually with semantic fallback.
"""
import argparse
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import torch
from sentence_transformers import SentenceTransformer, util

from ai_initializer import (
    CJK_RE,
    MODEL_NAME,
    SYN_THRESHOLD,
    TRANS_THRESHOLD,
    ensure_tables,
    persist_terms,
)


def normalize_en(text: Optional[str]) -> Optional[str]:
    return text.strip().lower() if text else None


def normalize_zh(text: Optional[str]) -> Optional[str]:
    return text.strip() if text else None


def detect_language(text: str) -> str:
    return "zh" if CJK_RE.search(text) else "en"


class NotebookApp:
    """Wraps DB + embedding model so we only load heavy assets once."""

    def __init__(self, db_path: Path, sql_dump: Optional[Path] = None, rebuild: bool = False):
        self.db_path = db_path
        if rebuild and db_path.exists():
            db_path.unlink()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        ensure_tables(self.conn)
        self.ensure_user_tables()
        if sql_dump:
            self.import_sql_dump(sql_dump)
            ensure_tables(self.conn)
            self.ensure_user_tables()
        self.model: Optional[SentenceTransformer] = None
        self._embed_cache: Dict[str, torch.Tensor] = {}

    # ---- schema helpers -------------------------------------------------
    def ensure_user_tables(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_vocab(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT,
                chinese TEXT,
                meaning_en TEXT,
                meaning_zh TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(english, chinese)
            );
            CREATE INDEX IF NOT EXISTS idx_user_vocab_en ON user_vocab(english);
            CREATE INDEX IF NOT EXISTS idx_user_vocab_zh ON user_vocab(chinese);
            CREATE INDEX IF NOT EXISTS idx_terms_lang_term ON terms(language, term);
            """
        )
        self.conn.commit()

    def import_sql_dump(self, sql_path: Path):
        """Stream-executes a .sql dump to hydrate the DB."""
        cur = self.conn.cursor()
        buffer: List[str] = []
        with sql_path.open(encoding="utf-8") as f:
            for line in f:
                buffer.append(line)
                if line.rstrip().endswith(";"):
                    cur.executescript("".join(buffer))
                    buffer.clear()
        if buffer:
            cur.executescript("".join(buffer))
        self.conn.commit()

    # ---- embeddings -----------------------------------------------------
    def _get_model(self) -> SentenceTransformer:
        if self.model is None:
            self.model = SentenceTransformer(MODEL_NAME)
        return self.model

    def _embed(self, text: str) -> torch.Tensor:
        if text not in self._embed_cache:
            vec = self._get_model().encode([text], convert_to_tensor=True, normalize_embeddings=True)[0]
            self._embed_cache[text] = vec
        return self._embed_cache[text]

    # ---- linking helpers ------------------------------------------------
    def _translation_score(
        self,
        english: Optional[str],
        chinese: Optional[str],
        meaning_en: Optional[str],
        meaning_zh: Optional[str],
    ) -> Optional[float]:
        left = english or meaning_en
        right = chinese or meaning_zh
        if not left or not right:
            return None
        return float(util.cos_sim(self._embed(left), self._embed(right)))

    def _upsert_translation_edge(
        self, english: Optional[str], chinese: Optional[str], meaning_en: Optional[str], meaning_zh: Optional[str]
    ) -> Optional[float]:
        if not english or not chinese:
            return None
        score = self._translation_score(english, chinese, meaning_en, meaning_zh)
        if score is None:
            return None
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO translation_edge(en_term, zh_term, score, source)
            VALUES (?, ?, ?, ?)
            """,
            (english, chinese, score, "user_input"),
        )
        self.conn.commit()
        return score

    def _candidate_terms(self, needle: str, language: str, limit: int) -> List[str]:
        pattern = f"%{needle}%"
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT term FROM terms
            WHERE language = ? AND term LIKE ?
            LIMIT ?
            """,
            (language, pattern, limit),
        )
        return [row[0] for row in cur.fetchall()]

    def _link_synonyms(
        self, term: Optional[str], language: str, contexts: Sequence[str], like_limit: int
    ) -> int:
        if not term:
            return 0
        seen: set[str] = set()
        candidates: List[str] = []
        for ctx in [term, *contexts]:
            if not ctx:
                continue
            for cand in self._candidate_terms(ctx, language, like_limit):
                if cand == term or cand in seen:
                    continue
                seen.add(cand)
                candidates.append(cand)
        if not candidates:
            return 0
        cand_vecs = self._get_model().encode(candidates, convert_to_tensor=True, normalize_embeddings=True)
        base_vec = self._embed(term)
        scores = util.cos_sim(base_vec, cand_vecs)[0]
        rows = []
        for cand, score in zip(candidates, scores):
            score_val = float(score)
            if score_val < SYN_THRESHOLD:
                continue
            left, right = sorted([term, cand])
            rows.append((left, right, language, score_val, "user_input"))
        if rows:
            cur = self.conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO synonym_edge(left_term, right_term, language, score, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.conn.commit()
        return len(rows)

    # ---- user operations ------------------------------------------------
    def record_vocab(
        self,
        english: Optional[str],
        chinese: Optional[str],
        meaning_en: Optional[str],
        meaning_zh: Optional[str],
        like_limit: int = 120,
    ) -> Dict[str, Optional[float]]:
        en_norm = normalize_en(english)
        zh_norm = normalize_zh(chinese)
        meaning_en = meaning_en.strip() if meaning_en else None
        meaning_zh = meaning_zh.strip() if meaning_zh else None
        if not en_norm and not zh_norm:
            raise ValueError("Provide at least one of --english/--chinese")
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO user_vocab(english, chinese, meaning_en, meaning_zh, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(english, chinese) DO UPDATE SET
                meaning_en = excluded.meaning_en,
                meaning_zh = excluded.meaning_zh,
                updated_at = CURRENT_TIMESTAMP
            """,
            (en_norm, zh_norm, meaning_en, meaning_zh),
        )
        self.conn.commit()
        vocab_terms = {t for t in (en_norm, zh_norm) if t}
        if vocab_terms:
            persist_terms(self.conn, vocab_terms)
        trans_score = self._upsert_translation_edge(en_norm, zh_norm, meaning_en, meaning_zh)
        en_links = self._link_synonyms(en_norm, "en", [meaning_en or ""], like_limit)
        zh_links = self._link_synonyms(zh_norm, "zh", [meaning_zh or ""], like_limit)
        return {"translation_score": trans_score, "en_links": en_links, "zh_links": zh_links}

    def _fetch_user_vocab(self) -> List[Dict[str, Optional[str]]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, english, chinese, meaning_en, meaning_zh FROM user_vocab")
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "id": row[0],
                    "english": row[1],
                    "chinese": row[2],
                    "meaning_en": row[3],
                    "meaning_zh": row[4],
                }
            )
        return rows

    def search_user_vocab(
        self, query: str, language: str, topk: int, include_base: int
    ) -> Tuple[List[Tuple[float, Dict[str, Optional[str]]]], List[Dict[str, object]]]:
        query = query.strip()
        lang = language if language != "auto" else detect_language(query)
        query_vec = self._embed(query)
        entries = self._fetch_user_vocab()
        scored: List[Tuple[float, Dict[str, Optional[str]]]] = []
        for entry in entries:
            fields: Iterable[Optional[str]]
            if lang == "en":
                fields = (entry["english"], entry["meaning_en"], entry["chinese"], entry["meaning_zh"])
            elif lang == "zh":
                fields = (entry["chinese"], entry["meaning_zh"], entry["english"], entry["meaning_en"])
            else:
                fields = (entry["english"], entry["chinese"], entry["meaning_en"], entry["meaning_zh"])
            best_score: Optional[float] = None
            for text in fields:
                if not text:
                    continue
                score = float(util.cos_sim(query_vec, self._embed(text)))
                if best_score is None or score > best_score:
                    best_score = score
            if best_score is not None:
                scored.append((best_score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        user_hits = scored[:topk]
        base_hits = self.search_base_dictionary(query, lang, include_base) if include_base else []
        return user_hits, base_hits

    def search_base_dictionary(self, query: str, language: str, limit: int) -> List[Dict[str, object]]:
        pattern = f"%{query}%"
        cur = self.conn.cursor()
        rows: List[Dict[str, object]] = []
        if language in {"en", "both"}:
            cur.execute(
                """
                SELECT en_term, zh_term, score FROM translation_edge
                WHERE en_term LIKE ?
                ORDER BY score DESC
                LIMIT ?
                """,
                (pattern, limit),
            )
            for en_term, zh_term, score in cur.fetchall():
                rows.append({"english": en_term, "chinese": zh_term, "score": score, "kind": "translation"})
            cur.execute(
                """
                SELECT left_term, right_term, score FROM synonym_edge
                WHERE language = 'en' AND (left_term LIKE ? OR right_term LIKE ?)
                ORDER BY score DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
            for left, right, score in cur.fetchall():
                rows.append({"english": left, "chinese": right, "score": score, "kind": "synonym"})
        if language in {"zh", "both"}:
            cur.execute(
                """
                SELECT en_term, zh_term, score FROM translation_edge
                WHERE zh_term LIKE ?
                ORDER BY score DESC
                LIMIT ?
                """,
                (pattern, limit),
            )
            for en_term, zh_term, score in cur.fetchall():
                rows.append({"english": en_term, "chinese": zh_term, "score": score, "kind": "translation"})
            cur.execute(
                """
                SELECT left_term, right_term, score FROM synonym_edge
                WHERE language = 'zh' AND (left_term LIKE ? OR right_term LIKE ?)
                ORDER BY score DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            )
            for left, right, score in cur.fetchall():
                rows.append({"english": left, "chinese": right, "score": score, "kind": "synonym"})
        rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)
        return rows[:limit]


def build_app(args: argparse.Namespace) -> NotebookApp:
    sql_dump = Path(args.sql_dump) if getattr(args, "sql_dump", None) else None
    return NotebookApp(Path(args.db), sql_dump=sql_dump, rebuild=getattr(args, "rebuild", False))


def cmd_init(args: argparse.Namespace):
    app = build_app(args)
    print(f"Database ready at {app.db_path}")


def cmd_record(args: argparse.Namespace):
    app = build_app(args)
    result = app.record_vocab(args.english, args.chinese, args.meaning_en, args.meaning_zh, args.link_limit)
    print("Saved vocab entry.")
    if result["translation_score"] is not None:
        print(f"translation_edge score={result['translation_score']:.3f}")
    print(f"linked {result['en_links']} English synonym edges, {result['zh_links']} Chinese synonym edges")


def cmd_search(args: argparse.Namespace):
    app = build_app(args)
    user_hits, base_hits = app.search_user_vocab(args.query, args.language, args.topk, args.include_base)
    print("User vocab hits:")
    for score, entry in user_hits:
        print(f"{score:.3f}\tEN: {entry['english'] or '-'}\tZH: {entry['chinese'] or '-'}")
        if entry.get("meaning_en"):
            print(f"  meaning_en: {entry['meaning_en']}")
        if entry.get("meaning_zh"):
            print(f"  meaning_zh: {entry['meaning_zh']}")
    if base_hits:
        print("\nBase dictionary hits:")
        for hit in base_hits:
            print(
                f"{hit.get('score', 0.0):.3f}\tEN: {hit.get('english') or '-'}\t"
                f"ZH: {hit.get('chinese') or '-'}\t[{hit.get('kind')}]"
            )


def main():
    parser = argparse.ArgumentParser(description="Vocab notebook main workflow")
    parser.add_argument("--db", default="notebook.db", help="SQLite path to read/write")
    parser.add_argument("--sql-dump", help="Optional .sql dump to hydrate the DB if missing")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create/open DB and optionally load a SQL dump")
    p_init.add_argument("--rebuild", action="store_true", help="Delete existing DB before loading dump")
    p_init.set_defaults(func=cmd_init)

    p_record = sub.add_parser("record", help="Record a new bilingual vocab entry")
    p_record.add_argument("--english", help="English vocab")
    p_record.add_argument("--chinese", help="Chinese vocab")
    p_record.add_argument("--meaning-en", dest="meaning_en", help="Meaning/explanation in English")
    p_record.add_argument("--meaning-zh", dest="meaning_zh", help="Meaning/explanation in Chinese")
    p_record.add_argument("--link-limit", type=int, default=120, help="Max LIKE candidates when linking synonyms")
    p_record.set_defaults(func=cmd_record)

    p_search = sub.add_parser("search", help="Search recorded vocab bilingually")
    p_search.add_argument("--query", required=True, help="Text to search for")
    p_search.add_argument("--language", choices=["auto", "en", "zh", "both"], default="auto", help="Language hint")
    p_search.add_argument("--topk", type=int, default=5, help="User vocab results to return")
    p_search.add_argument(
        "--include-base", type=int, default=5, help="Also return this many matches from the base dictionary tables"
    )
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
