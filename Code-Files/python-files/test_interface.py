"""Minimal test interface for ai_initializer.

Usage:
  python Code-Files/python-files/test_interface.py --db notebook.db --text "happy" --language en
  # or interactive mode
  python Code-Files/python-files/test_interface.py --db notebook.db --language en --interactive

If the DB is missing, pass --build to construct it first.
"""
import argparse
from pathlib import Path

from ai_initializer import build_edges, persist_edges, query_from_db


def ensure_db(db_path: Path, build: bool, syn_threshold: float, trans_threshold: float):
    if db_path.exists() and not build:
        return
    syn_edges, trans_edges, _, _, vocab = build_edges(syn_threshold, trans_threshold)
    persist_edges(db_path, syn_edges, trans_edges, vocab)


def run_once(db_path: Path, text: str, language: str, topk: int):
    results = query_from_db(db_path, text, language, topk)
    for term, score in results:
        print(f"{score:.3f}\t{term}")


def run_interactive(db_path: Path, language: str, topk: int):
    print(f"Interactive mode ({language}); type 'exit' to quit")
    while True:
        try:
            text = input(">> ").strip()
        except EOFError:
            break
        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue
        run_once(db_path, text, language, topk)


def main():
    parser = argparse.ArgumentParser(description="Simple test harness for ai_initializer")
    parser.add_argument("--db", default="notebook.db", help="SQLite path")
    parser.add_argument("--language", choices=["en", "zh"], default="en", help="Language to search")
    parser.add_argument("--text", help="Text to query once")
    parser.add_argument("--topk", type=int, default=10, help="Results to show")
    parser.add_argument("--build", action="store_true", help="Build DB before querying if missing")
    parser.add_argument("--syn-threshold", type=float, default=0.62, help="Synonym cosine threshold for build")
    parser.add_argument("--trans-threshold", type=float, default=0.48, help="Translation cosine threshold for build")
    parser.add_argument("--interactive", action="store_true", help="Run interactive query loop")
    args = parser.parse_args()

    db_path = Path(args.db)
    ensure_db(db_path, args.build, args.syn_threshold, args.trans_threshold)

    if args.interactive:
        run_interactive(db_path, args.language, args.topk)
    elif args.text:
        run_once(db_path, args.text, args.language, args.topk)
    else:
        parser.error("Provide --text for one-off query or --interactive")


if __name__ == "__main__":
<<<<<<< HEAD
    main()
=======
    main()
>>>>>>> 792df40 (lasdfsa)
