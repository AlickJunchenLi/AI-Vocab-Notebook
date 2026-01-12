import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from matching.tokens import extract_tokens  # noqa: E402
from matching.resolve import resolve_entry_candidates  # noqa: E402
from db import init_db, add_entry  # noqa: E402


def test_extract_tokens_mixed():
    text = "resilient的坚韧度 high-level 测试123"
    toks = extract_tokens(text)
    surfaces = [t["surface"] for t in toks]
    assert "resilient" in surfaces
    assert "坚韧度" in surfaces
    assert "high-level" in surfaces
    assert "测试123" in surfaces


def test_resolve_entry_exact_and_fuzzy():
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "test.db"
        init_db(db_path)
        # add entries
        add_entry(db_path, "en", "resilient", "韧性", "able to recover quickly")
        add_entry(db_path, "zh", "坚韧", "resilient", "")

        exact = resolve_entry_candidates(db_path, "resilient", "en", top_k=5)
        assert exact["best"] and exact["best"]["entry_id"] is not None

        fuzzy = resolve_entry_candidates(db_path, "renxing", None, top_k=5)
        assert fuzzy["candidates"], "should return fuzzy candidates even for transliteration-like strings"
