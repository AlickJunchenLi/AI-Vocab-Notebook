import re
from typing import List, Dict, Any


def extract_tokens(text: str) -> List[Dict[str, Any]]:
    """
    Extract tokens from mixed zh/en text.
    - English words (letters/digits/underscore, allow hyphen)
    - Chinese sequences that may include trailing digits (e.g., 测试123)
    """
    tokens: List[Dict[str, Any]] = []
    if not text:
        return tokens

    pattern_en = re.compile(r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*")
    pattern_zh = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fff0-9]*")

    matches: List[Dict[str, Any]] = []
    for m in pattern_en.finditer(text):
        matches.append({"start": m.start(), "end": m.end(), "surface": m.group(), "kind": "en"})
    for m in pattern_zh.finditer(text):
        start, end, surf = m.start(), m.end(), m.group()
        if surf.startswith("的") and len(surf) > 1:
            start += 1
            surf = surf[1:]
        if surf:
            matches.append({"start": start, "end": end, "surface": surf, "kind": "zh"})

    matches.sort(key=lambda x: x["start"])
    # remove overlaps by keeping earliest end
    filtered: List[Dict[str, Any]] = []
    last_end = -1
    for m in matches:
        if m["start"] >= last_end:
            filtered.append(m)
            last_end = m["end"]
    return filtered
