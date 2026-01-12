import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry  # noqa: E402
from server import handle_search_entries  # noqa: E402


def test_semantic_disabled_graceful():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        res = None
        try:
            res = handle_search_entries(db_path, {"q": "resilient", "mode": "semantic", "limit": 5})
        except Exception as exc:  # noqa: BLE001
            # handler should raise SemanticUnavailable -> mapped to error response in main loop,
            # but direct call here may still raise; ensure not ImportError
            assert "sentence_transformers" in str(exc) or "semantic" in str(exc).lower()
            return
        # if no exception, expect list or empty
        assert isinstance(res, list)


def test_semantic_with_dependency():
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        import pytest
        pytest.skip("sentence_transformers not installed")

    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "able to recover quickly")
        add_entry(db_path, "en", "robust", "强健", "similar meaning")
        res = handle_search_entries(db_path, {"q": "resilient", "mode": "semantic", "limit": 5})
        assert isinstance(res, list)
        assert len(res) >= 1
