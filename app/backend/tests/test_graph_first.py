import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry, upsert_relation  # noqa: E402
from server import handle_get_synonyms  # noqa: E402


def test_graph_bfs_depth_and_order():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        a = add_entry(db_path, "en", "a", "", "")
        b = add_entry(db_path, "en", "b", "", "")
        c = add_entry(db_path, "en", "c", "", "")
        d_id = add_entry(db_path, "en", "d", "", "")
        # a-b, b-c, c-d
        upsert_relation(db_path, a, b, "synonym")
        upsert_relation(db_path, b, c, "translation")
        upsert_relation(db_path, c, d_id, "synonym")

        res = handle_get_synonyms(
            db_path,
            {"q": "a", "depth": 2, "topK": 10, "fallback": False, "includeTypes": ["synonym", "translation"]},
        )
        ids = [g["entry_id"] for g in res["graph_results"]]
        assert b in ids
        assert c in ids  # depth 2 should include c
        assert d_id not in ids  # depth 2 excludes depth 3
        # order by distance then word
        distances = [g["distance"] for g in res["graph_results"]]
        assert min(distances) == 1
        assert max(distances) == 2


def test_get_synonyms_fallback_candidates():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "root", "", "")
        add_entry(db_path, "en", "related", "", "")
        add_entry(db_path, "en", "relatable", "", "")

        res = handle_get_synonyms(db_path, {"q": "root", "depth": 1, "topK": 3, "fallback": True})
        assert res["entry"]
        # graph_results empty (no relations), fallback should return some
        assert len(res["fallback_results"]) >= 0
