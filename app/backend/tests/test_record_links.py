import sys
import tempfile
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from db import init_db, add_entry  # noqa: E402
from server import (  # noqa: E402
    handle_add_record,
    handle_get_record,
    handle_link_record,
    handle_unlink_record,
)
from db import fetch_record_links  # noqa: E402


def run_cmd(handler, db_path, payload):
    return handler(db_path, payload)


def test_add_record_autolink_and_annotations():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        add_entry(db_path, "zh", "坚韧", "resilient", "")

        res = run_cmd(handle_add_record, db_path, {"text": "The resilient 品质展现出坚韧"})
        assert res["record_id"] > 0
        anns = res["annotations"]
        surfaces = [a["surface"] for a in anns]
        assert "resilient" in surfaces
        assert any("坚韧" in s for s in surfaces)
        res_ann = next(a for a in anns if a["surface"] == "resilient")
        assert res_ann["entry_id"] == 1
        links = fetch_record_links(db_path, res["record_id"])
        assert any(l["entry_id"] == 1 for l in links)


def test_link_overrides_same_span_and_unlink():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        add_entry(db_path, "en", "tough", "顽强", "")

        add_res = run_cmd(handle_add_record, db_path, {"text": "resilient"})
        rid = add_res["record_id"]
        ann = add_res["annotations"][0]
        link_res = run_cmd(
            handle_link_record,
            db_path,
            {
                "record_id": rid,
                "entry_id": 2,
                "start": ann["start"],
                "end": ann["end"],
                "surface": ann["surface"],
            },
        )
        assert link_res["ok"]
        latest = run_cmd(handle_get_record, db_path, {"record_id": rid})
        linked_ann = latest["annotations"][0]
        assert linked_ann["entry_id"] == 2
        # only one link for that span
        links = fetch_record_links(db_path, rid)
        assert len(links) == 1 and links[0]["entry_id"] == 2

        unlink_res = run_cmd(
            handle_unlink_record,
            db_path,
            {
                "record_id": rid,
                "entry_id": 2,
                "start": ann["start"],
                "end": ann["end"],
            },
        )
        assert unlink_res["ok"]
        latest2 = run_cmd(handle_get_record, db_path, {"record_id": rid})
        assert latest2["annotations"][0]["entry_id"] is None
        links2 = fetch_record_links(db_path, rid)
        assert links2 == []


def test_mixed_language_tokens_annotations_refresh():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "concise", "简洁", "")
        add_entry(db_path, "zh", "简洁", "concise", "")

        res = run_cmd(handle_add_record, db_path, {"text": "简洁 concise"})
        rid = res["record_id"]
        anns = res["annotations"]
        surfaces = [a["surface"] for a in anns]
        assert "简洁" in surfaces
        assert "concise" in surfaces
    ids = [a["entry_id"] for a in anns]
    assert ids.count(None) < len(ids)


def test_link_bad_range():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        add_entry(db_path, "en", "resilient", "韧性", "")
        add_res = run_cmd(handle_add_record, db_path, {"text": "resilient"})
        rid = add_res["record_id"]
        ann = add_res["annotations"][0]
        with pytest.raises(ValueError):
            handle_link_record(
                db_path,
                {
                    "record_id": rid,
                    "entry_id": 1,
                    "start": ann["end"],
                    "end": ann["start"],  # bad range
                    "surface": ann["surface"],
                },
            )
