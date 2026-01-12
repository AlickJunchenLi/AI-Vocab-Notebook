import argparse
import csv
import re
import sqlite3
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import torch
from sentence_transformers import SentenceTransformer, util

# Data locations
DATA_ROOT = Path("Unchanged-Databases")
EN_SYNONYMS = DATA_ROOT / "English_Thesaurus" / "WordnetThesaurus.csv"
ZH_SYNONYMS = DATA_ROOT / "Chinese_Thesaurus" / "cn_thesaurus.txt"
TRANSLATIONS = DATA_ROOT / "Translation_Dictionary" / "ecdict.csv"

# Model + scoring defaults
MODEL_NAME = "intfloat/multilingual-e5-small"
SYN_THRESHOLD = 0.62
TRANS_THRESHOLD = 0.48
BATCH_SIZE = 256

CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def clean_translation_field(raw: str) -> List[str]:
    """Parse the translation column into candidate Chinese terms."""
    raw = re.sub(r"\[.*?\]|\(.*?\)", "", raw)
    raw = raw.replace("\u3000", " ")  # full-width space
    raw = re.sub(r"[;\uFF1B/\u3001]+", ",", raw)
    out: List[str] = []
    for part in raw.split(","):
        tok = part.strip()
        if not tok or not CJK_RE.search(tok):
            continue
        punct_ratio = sum(ch in ".,;\uFF0C\u3001/()[]" for ch in tok) / len(tok)
        if punct_ratio > 0.3 or len(tok) > 30:
            continue
        out.append(tok)
    return out


def iter_en_synonym_groups(path: Path) -> Iterable[List[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            tokens = [col.strip().lower() for col in row if col.strip()]
            if len(tokens) > 1:
                yield tokens


def iter_zh_synonym_groups(path: Path) -> Iterable[List[str]]:
    with path.open(encoding="utf-8") as f:
        for raw in f:
            tokens = [p.strip().lower() for p in re.split(r"[,\uFF0C\s]+", raw) if p.strip()]
            if len(tokens) > 1:
                yield tokens


def iter_translation_pairs(path: Path) -> Iterable[Tuple[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            en = (row.get("word") or "").strip().lower()
            if not en:
                continue
            for zh in clean_translation_field(row.get("translation", "")):
                yield en, zh


def encode_terms(terms: Sequence[str], model: SentenceTransformer) -> Dict[str, torch.Tensor]:
    """Embed all terms with normalization and return a term->vector map."""
    out: Dict[str, torch.Tensor] = {}
    for i in range(0, len(terms), BATCH_SIZE):
        chunk = terms[i : i + BATCH_SIZE]
        vecs = model.encode(chunk, convert_to_tensor=True, normalize_embeddings=True)
        for term, vec in zip(chunk, vecs):
            out[term] = vec
    return out


def score_synonym_edges(groups: List[List[str]], emb_map: Dict[str, torch.Tensor], language: str, threshold: float):
    edges = []
    for group in groups:
        uniq = sorted(set(group))
        for a, b in combinations(uniq, 2):
            va, vb = emb_map.get(a), emb_map.get(b)
            if va is None or vb is None:
                continue
            score = float(util.cos_sim(va, vb))
            if score >= threshold:
                edges.append((a, b, language, score, "thesaurus"))
    return edges


def score_translation_edges(pairs: List[Tuple[str, str]], emb_map: Dict[str, torch.Tensor], threshold: float):
    edges = []
    for en, zh in pairs:
        ve, vz = emb_map.get(en), emb_map.get(zh)
        if ve is None or vz is None:
            continue
        score = float(util.cos_sim(ve, vz))
        if score >= threshold:
            edges.append((en, zh, score, "translation"))
    return edges


def ensure_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS synonym_edge(
            id INTEGER PRIMARY KEY,
            left_term TEXT,
            right_term TEXT,
            language TEXT,
            score REAL,
            source TEXT,
            UNIQUE(left_term, right_term, language, source)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS translation_edge(
            id INTEGER PRIMARY KEY,
            en_term TEXT,
            zh_term TEXT,
            score REAL,
            source TEXT,
            UNIQUE(en_term, zh_term, source)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS terms(
            term TEXT PRIMARY KEY,
            language TEXT
        )
        """
    )
    conn.commit()


def persist_terms(conn: sqlite3.Connection, vocab: Set[str]):
    cur = conn.cursor()
    rows = []
    for term in vocab:
        lang = "zh" if CJK_RE.search(term) else "en"
        rows.append((term, lang))
    cur.executemany(
        "INSERT OR IGNORE INTO terms(term, language) VALUES (?, ?)",
        rows,
    )
    conn.commit()


def persist_edges(db_path: Path, syn_edges, trans_edges, vocab: Set[str]):
    conn = sqlite3.connect(db_path)
    ensure_tables(conn)
    persist_terms(conn, vocab)
    cur = conn.cursor()
    cur.executemany(
        """INSERT OR REPLACE INTO synonym_edge(left_term, right_term, language, score, source)
               VALUES (?, ?, ?, ?, ?)""",
        syn_edges,
    )
    cur.executemany(
        """INSERT OR REPLACE INTO translation_edge(en_term, zh_term, score, source)
               VALUES (?, ?, ?, ?)""",
        trans_edges,
    )
    conn.commit()
    conn.close()


def build_edges(syn_threshold: float, trans_threshold: float):
    en_groups = list(iter_en_synonym_groups(EN_SYNONYMS))
    zh_groups = list(iter_zh_synonym_groups(ZH_SYNONYMS))
    translation_pairs = list(iter_translation_pairs(TRANSLATIONS))

    vocab = sorted({w for g in en_groups + zh_groups for w in g} | {w for pair in translation_pairs for w in pair})
    model = SentenceTransformer(MODEL_NAME)
    emb_map = encode_terms(vocab, model)

    syn_edges = []
    syn_edges.extend(score_synonym_edges(en_groups, emb_map, "en", syn_threshold))
    syn_edges.extend(score_synonym_edges(zh_groups, emb_map, "zh", syn_threshold))
    trans_edges = score_translation_edges(translation_pairs, emb_map, trans_threshold)
    return syn_edges, trans_edges, emb_map, model, set(vocab)


def collect_terms_for_language(db_path: Path, language: str) -> List[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    terms: set[str] = set()
    cur.execute("SELECT term FROM terms WHERE language = ?", (language,))
    fetched = [t[0] for t in cur.fetchall()]
    if fetched:
        terms.update(fetched)
    else:
        # Fallback: derive from edges if terms table was not populated
        if language == "en":
            cur.execute("SELECT left_term, right_term FROM synonym_edge WHERE language = 'en'")
            for a, b in cur.fetchall():
                terms.add(a)
                terms.add(b)
            cur.execute("SELECT en_term FROM translation_edge")
            terms.update(t[0] for t in cur.fetchall())
        else:
            cur.execute("SELECT left_term, right_term FROM synonym_edge WHERE language = 'zh'")
            for a, b in cur.fetchall():
                terms.add(a)
                terms.add(b)
            cur.execute("SELECT zh_term FROM translation_edge")
            terms.update(t[0] for t in cur.fetchall())
    conn.close()
    return sorted(t for t in terms if t)


def encode_term_list(terms: Sequence[str], model: SentenceTransformer) -> torch.Tensor:
    vecs: List[torch.Tensor] = []
    for i in range(0, len(terms), BATCH_SIZE):
        chunk = terms[i : i + BATCH_SIZE]
        chunk_vecs = model.encode(chunk, convert_to_tensor=True, normalize_embeddings=True)
        vecs.append(chunk_vecs)
    return torch.cat(vecs, dim=0) if vecs else torch.empty((0,))


def query_from_db(db_path: Path, text: str, language: str, top_k: int = 10):
    model = SentenceTransformer(MODEL_NAME)
    terms = collect_terms_for_language(db_path, language)
    if not terms:
        return []
    term_vecs = encode_term_list(terms, model)
    query_vec = model.encode([text], convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_vec, term_vecs)[0]
    k = min(top_k, scores.shape[0])
    values, indices = torch.topk(scores, k)
    return [(terms[idx], float(val)) for val, idx in zip(values, indices)]


def query_in_memory(text: str, language: str, emb_map: Dict[str, torch.Tensor], model: SentenceTransformer, top_k: int = 10):
    query_vec = model.encode([text], convert_to_tensor=True, normalize_embeddings=True)
    scored = []
    for term, vec in emb_map.items():
        is_zh = bool(CJK_RE.search(term))
        if language == "en" and is_zh:
            continue
        if language == "zh" and not is_zh:
            continue
        scored.append((term, float(util.cos_sim(query_vec, vec))))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def run_build(args):
    syn_edges, trans_edges, _, _, vocab = build_edges(args.syn_threshold, args.trans_threshold)
    persist_edges(Path(args.db), syn_edges, trans_edges, vocab)
    print(
        f"Persisted {len(vocab)} terms, {len(syn_edges)} synonym edges, and {len(trans_edges)} translation edges to {args.db}"
    )


def run_query(args):
    results = query_from_db(Path(args.db), args.text, args.language, args.topk)
    for term, score in results:
        print(f"{score:.3f}\t{term}")


def main():
    parser = argparse.ArgumentParser(description="AI initializer for vocab notebook")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Parse datasets, score edges, and persist to SQLite")
    p_build.add_argument("--db", default="notebook.db", help="SQLite path to write edges")
    p_build.add_argument("--syn-threshold", type=float, default=SYN_THRESHOLD, help="Cosine threshold for synonyms")
    p_build.add_argument("--trans-threshold", type=float, default=TRANS_THRESHOLD, help="Cosine threshold for translations")
    p_build.set_defaults(func=run_build)

    p_query = sub.add_parser("query", help="Embed client text and return nearest terms from DB")
    p_query.add_argument("--db", default="notebook.db", help="SQLite path with edges")
    p_query.add_argument("--text", required=True, help="Client input text")
    p_query.add_argument("--language", choices=["en", "zh"], default="en", help="Language to search within")
    p_query.add_argument("--topk", type=int, default=10, help="Number of results to return")
    p_query.set_defaults(func=run_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
