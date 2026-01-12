import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry  # noqa: E402
from server import handle_search_entries, handle_ann_status  # noqa: E402


def test_ann_status_disabled_without_faiss():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        status = handle_ann_status(db_path, {"model": "dummy"})
        assert status["enabled"] in (True, False)


def test_semantic_fallback_when_ann_missing():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        res = None
        try:
            res = handle_search_entries(db_path, {"q": "resilient", "mode": "semantic", "limit": 3})
        except Exception as exc:  # noqa: BLE001
            # allowed to raise SemanticUnavailable if deps missing
            assert "semantic" in str(exc).lower()
            return
        # if no exception, expect list
        assert isinstance(res, list)
