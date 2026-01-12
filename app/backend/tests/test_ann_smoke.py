import sys
import tempfile
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry  # noqa: E402
from semantic import ensure_embedding_for_entry  # noqa: E402
from server import handle_rebuild_ann_index, handle_search_entries  # noqa: E402


def test_ann_smoke_with_faiss_and_sentence_transformers():
    faiss = pytest.importorskip("faiss")
    st = pytest.importorskip("sentence_transformers")
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        e1 = add_entry(db_path, "en", "resilient", "韧性", "able to recover quickly")
        e2 = add_entry(db_path, "en", "robust", "强健", "similar meaning")
        e3 = add_entry(db_path, "en", "cat", "猫", "animal")

        ensure_embedding_for_entry(db_path, e1)
        ensure_embedding_for_entry(db_path, e2)
        ensure_embedding_for_entry(db_path, e3)

        rebuilt = handle_rebuild_ann_index(db_path, {"model": None})
        assert rebuilt >= 3

        res = handle_search_entries(db_path, {"q": "resilient", "mode": "semantic", "limit": 3})
        assert isinstance(res, list)
        ids = [r["id"] for r in res]
        assert e1 in ids or e2 in ids
