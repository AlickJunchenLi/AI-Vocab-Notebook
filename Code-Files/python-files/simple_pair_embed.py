# -*- coding: utf-8 -*-
"""Embed two terms and report cosine similarity + pass/fail.

Example:
  python Code-Files/python-files/simple_pair_embed.py --w1 "happy" --w2 "glad" --language en
  python Code-Files/python-files/simple_pair_embed.py --w1 "happy" --w2 "快乐" --language zh
"""
import argparse
import re
from typing import Tuple

import torch
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_THRESHOLD = 0.60
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def normalize(term: str, language: str) -> str:
    term = term.strip()
    if language == "en":
        term = term.lower()
    return term


def infer_language(term: str) -> str:
    return "zh" if CJK_RE.search(term) else "en"


def score_pair(w1: str, w2: str, language: str, threshold: float) -> Tuple[float, bool]:
    model = SentenceTransformer(MODEL_NAME)
    terms = [normalize(w1, language), normalize(w2, language)]
    vecs = model.encode(terms, convert_to_tensor=True, normalize_embeddings=True)
    score = float(util.cos_sim(vecs[0], vecs[1]))
    return score, score >= threshold


def main():
    parser = argparse.ArgumentParser(description="Embed two terms and check similarity")
    parser.add_argument("--w1", required=True, help="First word")
    parser.add_argument("--w2", required=True, help="Second word")
    parser.add_argument("--language", choices=["en", "zh", "auto"], default="auto", help="Language for normalization; auto uses basic script detection")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Cosine threshold to consider similar")
    args = parser.parse_args()

    lang = args.language
    if lang == "auto":
        l1 = infer_language(args.w1)
        l2 = infer_language(args.w2)
        lang = "zh" if l1 == "zh" or l2 == "zh" else "en"

    score, is_similar = score_pair(args.w1, args.w2, lang, args.threshold)
    print(f"similar={is_similar}")
    print(f"score={score:.3f}")
    print(f"language_used={lang}")


if __name__ == "__main__":
    main()
