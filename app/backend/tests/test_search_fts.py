import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry  # noqa: E402
from search import search_fts  # noqa: E402


def test_search_fts_matches_word_translation_notes():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "able to recover quickly")
        add_entry(db_path, "zh", "协作", "collaboration", "working jointly")

        res_word = search_fts(db_path, "resilient", limit=10, offset=0)
        assert any(r["word"] == "resilient" for r in res_word)

        res_trans = search_fts(db_path, "韧性", limit=10, offset=0)
        assert any(r["translation"] == "韧性" for r in res_trans)

        res_notes = search_fts(db_path, "recover", limit=10, offset=0)
        assert any("resilient" == r["word"] for r in res_notes)


def test_search_fts_order_and_match_type():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "abc", "x", "")
        add_entry(db_path, "en", "abcd", "y", "")

        res = search_fts(db_path, "abc*", limit=10, offset=0)
        assert len(res) >= 2
        assert all(r.get("match_type") == "fts" for r in res)
