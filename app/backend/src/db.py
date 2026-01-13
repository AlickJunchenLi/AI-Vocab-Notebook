import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from difflib import SequenceMatcher

DB_VERSION = 7


def _safe_text(val: Any) -> str:
    """
    Normalize text inputs to avoid UnicodeEncodeError from lone surrogates
    when writing to SQLite or JSON.
    """
    if val is None:
        return ""
    if not isinstance(val, str):
        val = str(val)
    return val.encode("utf-8", "surrogatepass").decode("utf-8", "replace")


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(db_path))


def _get_version(cur) -> int:
    cur.execute("PRAGMA user_version;")
    row = cur.fetchone()
    return row[0] if row else 0


def _migrate(conn: sqlite3.Connection):
    cur = conn.cursor()
    ver = _get_version(cur)
    # ensure deleted_at column exists even if table already created in older version
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries';")
    has_entries = cur.fetchone() is not None
    if has_entries:
        cur.execute("PRAGMA table_info(entries);")
        cols = [row[1] for row in cur.fetchall()]
        if "deleted_at" not in cols:
            cur.execute("ALTER TABLE entries ADD COLUMN deleted_at REAL;")
        if "notes" not in cols:
            cur.execute("ALTER TABLE entries ADD COLUMN notes TEXT;")
    if ver < 1:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT NOT NULL,
                word TEXT NOT NULL,
                translation TEXT,
                notes TEXT,
                created_at REAL,
                updated_at REAL,
                deleted_at REAL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                created_at REAL,
                FOREIGN KEY(from_id) REFERENCES entries(id),
                FOREIGN KEY(to_id) REFERENCES entries(id)
            );
            """
        )
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_relations_uniq ON relations(from_id, to_id, type);")
        cur.execute("PRAGMA user_version = 1;")
        ver = 1
    if ver < 2:
        cur.execute("PRAGMA user_version = 2;")
        ver = 2
    if ver < 3:
        cur.execute("PRAGMA table_info(entries);")
        cols = [row[1] for row in cur.fetchall()]
        if "notes" not in cols:
            cur.execute("ALTER TABLE entries ADD COLUMN notes TEXT;")
        cur.execute("PRAGMA user_version = 3;")
        ver = 3
    if ver < 4:
        # records table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                created_at REAL,
                updated_at REAL
            );
            """
        )
        # record_links
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS record_links(
                record_id INTEGER NOT NULL,
                entry_id INTEGER NOT NULL,
                start INTEGER NOT NULL,
                "end" INTEGER NOT NULL,
                surface TEXT,
                match_type TEXT,
                score REAL,
                created_at REAL,
                FOREIGN KEY(record_id) REFERENCES records(id),
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_record_links_record ON record_links(record_id);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_record_links_entry ON record_links(entry_id);"
        )
        cur.execute("PRAGMA user_version = 4;")
        ver = 4
    if ver < 5:
        # FTS5 for entries
        cur.execute("DROP TRIGGER IF EXISTS trg_entries_ai_fts;")
        cur.execute("DROP TRIGGER IF EXISTS trg_entries_ad_fts;")
        cur.execute("DROP TRIGGER IF EXISTS trg_entries_au_fts;")
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                word, translation, notes, content='entries', content_rowid='id'
            );
            """
        )
        cur.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild');")
        cur.execute(
            """
            CREATE TRIGGER trg_entries_ai_fts AFTER INSERT ON entries BEGIN
                INSERT INTO entries_fts(rowid, word, translation, notes)
                VALUES (new.id, new.word, new.translation, new.notes);
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER trg_entries_ad_fts AFTER DELETE ON entries BEGIN
                DELETE FROM entries_fts WHERE rowid = old.id;
            END;
            """
        )
        cur.execute(
            """
            CREATE TRIGGER trg_entries_au_fts AFTER UPDATE ON entries BEGIN
                DELETE FROM entries_fts WHERE rowid = old.id;
                INSERT INTO entries_fts(rowid, word, translation, notes)
                VALUES (new.id, new.word, new.translation, new.notes);
            END;
            """
        )
        cur.execute("PRAGMA user_version = 5;")
        ver = 5
    if ver < 6:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entry_embeddings(
                entry_id INTEGER PRIMARY KEY,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                vec BLOB NOT NULL,
                updated_at REAL,
                FOREIGN KEY(entry_id) REFERENCES entries(id)
            );
            """
        )
        cur.execute("PRAGMA user_version = 6;")
        ver = 6
    if ver < 7:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ann_queue(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                op TEXT NOT NULL,
                queued_at REAL,
                reason TEXT
            );
            """
        )
        cur.execute("PRAGMA user_version = 7;")
        ver = 7
    if ver < DB_VERSION:
        cur.execute("PRAGMA user_version = ?;", (DB_VERSION,))
    conn.commit()


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    _migrate(conn)
    conn.close()


def add_entry(db_path: Path, language: str, word: str, translation: str, notes: str = "") -> int:
    now = time.time()
    language = _safe_text(language)
    word = _safe_text(word)
    translation = _safe_text(translation)
    notes = _safe_text(notes)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO entries(language, word, translation, notes, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (language, word, translation, notes, now, now),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def update_entry(db_path: Path, entry_id: int, language: str, word: str, translation: str, notes: str = "") -> bool:
    now = time.time()
    language = _safe_text(language)
    word = _safe_text(word)
    translation = _safe_text(translation)
    notes = _safe_text(notes)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE entries
        SET language = ?, word = ?, translation = ?, notes = ?, updated_at = ?
        WHERE id = ? AND deleted_at IS NULL
        """,
        (language, word, translation, notes, now, entry_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def soft_delete_entry(db_path: Path, entry_id: int) -> bool:
    now = time.time()
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE entries SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
        (now, entry_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def get_entry(db_path: Path, entry_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, language, word, translation, notes, created_at, updated_at, deleted_at FROM entries WHERE id = ?",
        (entry_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "language": row[1],
        "word": row[2],
        "translation": row[3],
        "notes": row[4],
        "created_at": row[5],
        "updated_at": row[6],
        "deleted_at": row[7],
    }


def list_entries(db_path: Path, limit: int = 50, offset: int = 0, include_deleted: bool = False) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    if include_deleted:
        cur.execute(
            """
            SELECT id, language, word, translation, notes, created_at, updated_at, deleted_at
            FROM entries
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
    else:
        cur.execute(
            """
            SELECT id, language, word, translation, notes, created_at, updated_at, deleted_at
            FROM entries
            WHERE deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "language": r[1],
            "word": r[2],
            "translation": r[3],
            "notes": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "deleted_at": r[7],
        }
        for r in rows
    ]


def upsert_relation(db_path: Path, from_id: int, to_id: int, rel_type: str) -> int:
    now = time.time()
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO relations(from_id, to_id, type, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(from_id, to_id, type) DO UPDATE SET created_at = excluded.created_at
        """,
        (from_id, to_id, rel_type, now),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def list_relations(db_path: Path, entry_id: int) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, from_id, to_id, type, created_at
        FROM relations
        WHERE from_id = ? OR to_id = ?
        ORDER BY created_at DESC
        """,
        (entry_id, entry_id),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "from_id": r[1], "to_id": r[2], "type": r[3], "created_at": r[4]}
        for r in rows
    ]


def get_entries_by_ids(db_path: Path, ids: List[int]) -> List[Dict[str, Any]]:
    if not ids:
        return []
    conn = _connect(db_path)
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(ids))
    cur.execute(
        f"""
        SELECT id, language, word, translation, notes, created_at, updated_at, deleted_at
        FROM entries
        WHERE id IN ({placeholders}) AND deleted_at IS NULL
        """,
        ids,
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "language": r[1],
            "word": r[2],
            "translation": r[3],
            "notes": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "deleted_at": r[7],
        }
        for r in rows
    ]


def find_translation_matches(db_path: Path, language: str, translation: str) -> List[int]:
    """
    Find entries in any language whose word or translation looks like the provided translation string.
    This is used to connect cross-language pairs even if only one side exists.
    """
    language = _safe_text(language)
    translation = _safe_text(translation)
    if not translation:
        return []
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, word, translation FROM entries
        WHERE deleted_at IS NULL
        """,
    )
    rows = cur.fetchall()
    conn.close()
    matches: List[int] = []
    seen = set()
    for entry_id, word_val, trans_val in rows:
        best_score = 0.0
        if word_val:
            best_score = max(best_score, SequenceMatcher(None, translation, word_val).ratio())
        if trans_val:
            best_score = max(best_score, SequenceMatcher(None, translation, trans_val).ratio())
        if best_score >= 0.5 and entry_id not in seen:
            matches.append(entry_id)
            seen.add(entry_id)
    return matches


def find_synonym_matches(db_path: Path, language: str, word: str, translation: str = "", threshold: float = 0.6) -> List[int]:
    """
    Find entries that look like synonyms by comparing both the word and translation fields.
    - Same-language words use a lenient similarity threshold.
    - Cross-language comparisons rely on translation/word overlap.
    """
    language = _safe_text(language)
    word = _safe_text(word)
    translation = _safe_text(translation)
    if not word and not translation:
        return []
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, language, word, translation
        FROM entries
        WHERE deleted_at IS NULL
        """
    )
    rows = cur.fetchall()
    conn.close()
    matches: List[int] = []
    seen = set()
    for entry_id, lang_val, other_word, other_trans in rows:
        if entry_id in seen:
            continue
        best_score = 0.0
        # same-language word similarity
        if word and other_word and lang_val == language:
            best_score = max(best_score, SequenceMatcher(None, word, other_word).ratio())
        # translation similarity (cross or same language)
        if translation and other_trans:
            best_score = max(best_score, SequenceMatcher(None, translation, other_trans).ratio())
        # cross-field overlap to catch translated synonyms
        if translation and other_word:
            best_score = max(best_score, SequenceMatcher(None, translation, other_word).ratio())
        if word and other_trans:
            best_score = max(best_score, SequenceMatcher(None, word, other_trans).ratio())
        if best_score >= threshold:
            matches.append(entry_id)
            seen.add(entry_id)
    return matches


# Records + links helpers
def add_record(db_path: Path, text: str) -> int:
    now = time.time()
    text = _safe_text(text)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO records(text, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (text, now, now),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_record(db_path: Path, record_id: int, text: str) -> bool:
    now = time.time()
    text = _safe_text(text)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE records SET text = ?, updated_at = ? WHERE id = ?
        """,
        (text, now, record_id),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def get_record(db_path: Path, record_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, text, created_at, updated_at FROM records WHERE id = ?
        """,
        (record_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "text": row[1], "created_at": row[2], "updated_at": row[3]}


def list_records(db_path: Path, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, text, created_at, updated_at
        FROM records
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "text": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]


def replace_record_links(db_path: Path, record_id: int, links: List[Dict[str, Any]]):
    conn = _connect(db_path)
    cur = conn.cursor()
    now = time.time()
    cur.execute("DELETE FROM record_links WHERE record_id = ?", (record_id,))
    if links:
        cur.executemany(
            """
            INSERT INTO record_links(record_id, entry_id, start, "end", surface, match_type, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record_id,
                    l["entry_id"],
                    l["start"],
                    l["end"],
                    _safe_text(l.get("surface", "")),
                    _safe_text(l.get("match_type", "")),
                    l.get("score", 0.0),
                    now,
                )
                for l in links
            ],
        )
    conn.commit()
    conn.close()


def fetch_record_links(db_path: Path, record_id: int) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT record_id, entry_id, start, "end", surface, match_type, score, created_at
        FROM record_links
        WHERE record_id = ?
        ORDER BY start ASC
        """,
        (record_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "record_id": r[0],
            "entry_id": r[1],
            "start": r[2],
            "end": r[3],
            "surface": r[4],
            "match_type": r[5],
            "score": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]


# ANN queue helpers
def enqueue_ann_op(db_path: Path, entry_id: int, op: str, reason: str = ""):
    now = time.time()
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ann_queue(entry_id, op, queued_at, reason)
        VALUES(?, ?, ?, ?)
        """,
        (entry_id, op, now, reason),
    )
    conn.commit()
    conn.close()


def fetch_ann_queue(db_path: Path, max_n: int = 200) -> List[Dict[str, Any]]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, entry_id, op, queued_at, reason
        FROM ann_queue
        ORDER BY id ASC
        LIMIT ?
        """,
        (max_n,),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "entry_id": r[1], "op": r[2], "queued_at": r[3], "reason": r[4]} for r in rows]


def clear_ann_queue(db_path: Path, ids: List[int]):
    if not ids:
        return
    conn = _connect(db_path)
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(ids))
    cur.execute(f"DELETE FROM ann_queue WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


def count_ann_queue(db_path: Path) -> int:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ann_queue")
    n = cur.fetchone()[0]
    conn.close()
    return n
