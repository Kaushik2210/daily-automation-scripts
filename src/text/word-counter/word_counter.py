"""Count lines, words and characters in text files, with optional top words."""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

WORD_RE = re.compile(r"[\w']+")


def count_text(text):
    """Return a dict with line, word, character and byte counts for a string."""
    return {
        "lines": len(text.splitlines()),
        "words": len(text.split()),
        "chars": len(text),
        "bytes": len(text.encode("utf-8")),
    }


def top_words(text, limit=10, min_length=3):
    words = (w.lower() for w in WORD_RE.findall(text))
    counter = Counter(w for w in words if len(w) >= min_length)
    return counter.most_common(limit)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count lines, words and characters.")
    parser.add_argument("files", nargs="*", type=Path, help="files to read (default: stdin)")
    parser.add_argument("--top", type=int, default=0, help="also list the N most common words")
    args = parser.parse_args(argv)

    texts = {}
    if args.files:
        for path in args.files:
            try:
                texts[str(path)] = path.read_text(encoding="utf-8", errors="replace")
            except OSError as err:
                print(f"{path}: {err}", file=sys.stderr)
    else:
        texts["<stdin>"] = sys.stdin.read()

    print(f"{'lines':>8}{'words':>8}{'chars':>10}{'bytes':>10}  file")
    for name, text in texts.items():
        c = count_text(text)
        print(f"{c['lines']:>8}{c['words']:>8}{c['chars']:>10}{c['bytes']:>10}  {name}")
    if args.top:
        print("\nMost common words:")
        for word, count in top_words("\n".join(texts.values()), args.top):
            print(f"{count:>6}  {word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
