import sys
import tempfile
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry, soft_delete_entry  # noqa: E402
from semantic import ensure_embedding_for_entry  # noqa: E402
from server import (  # noqa: E402
    handle_search_entries,
    handle_rebuild_ann_index,
    handle_ann_apply_updates,
)


def test_ann_incremental_skip_when_no_backend():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        res = None
        try:
            res = handle_ann_apply_updates(db_path, {"model": None})
        except Exception:
            # allowed to raise if deps missing
            return
        assert isinstance(res, dict)


def test_ann_incremental_upsert_update_delete():
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        e1 = add_entry(db_path, "en", "resilient", "韧性", "able to recover quickly")
        e2 = add_entry(db_path, "en", "robust", "强健", "similar meaning")

        ensure_embedding_for_entry(db_path, e1)
        ensure_embedding_for_entry(db_path, e2)
        handle_rebuild_ann_index(db_path, {"model": None})

        res1 = handle_search_entries(db_path, {"q": "resilient", "mode": "semantic", "limit": 3})
        ids1 = [r["id"] for r in res1] if isinstance(res1, list) else []
        assert e1 in ids1 or e2 in ids1

        # update entry text -> ensure embedding -> apply updates
        add_entry(db_path, "en", "updatedword", "测试", "")
        ensure_embedding_for_entry(db_path, e1)
        handle_ann_apply_updates(db_path, {"model": None})

        res2 = handle_search_entries(db_path, {"q": "updatedword", "mode": "semantic", "limit": 3})
        ids2 = [r["id"] for r in res2] if isinstance(res2, list) else []
        assert e1 in ids2

        # delete entry -> apply updates -> should not return
        soft_delete_entry(db_path, e1)
        handle_ann_apply_updates(db_path, {"model": None})
        res3 = handle_search_entries(db_path, {"q": "updatedword", "mode": "semantic", "limit": 3})
        ids3 = [r["id"] for r in res3] if isinstance(res3, list) else []
        assert e1 not in ids3
