"""Find words that are not in a word list, with spelling suggestions."""
import argparse
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

SYSTEM_LISTS = [Path("/usr/share/dict/words"), Path("/usr/share/dict/american-english"),
                Path("/usr/dict/words")]
SKIP = re.compile(r"https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+|`[^`]*`")


def load_words(path):
    return {line.strip().lower() for line in path.read_text(encoding="utf-8", errors="replace")
            .splitlines() if line.strip() and not line.startswith("#")}


def find_unknown(text, known, ignore_capitalized=False):
    """Return {word: [line numbers]} for words not in `known`."""
    found = defaultdict(list)
    for number, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"[A-Za-z][A-Za-z']*[A-Za-z]|[A-Za-z]", SKIP.sub(" ", line)):
            word = match.group(0)
            lowered = word.lower().removesuffix("'s")
            if (lowered in known or len(lowered) < 2 or word.isupper()
                    or (ignore_capitalized and word[0].isupper())):
                continue
            found[lowered].append(number)
    return found


def suggest(word, known_sorted, limit=3):
    return difflib.get_close_matches(word, known_sorted, n=limit, cutoff=0.75)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Find unknown words against a word list.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--wordlist", type=Path, help="one word per line (default: system list)")
    parser.add_argument("--allow", type=Path, action="append", default=[],
                        help="extra accepted words (names, jargon); can be repeated")
    parser.add_argument("--ignore-capitalized", action="store_true",
                        help="don't report capitalised words (names, places)")
    args = parser.parse_args(argv)

    wordlist = args.wordlist or next((p for p in SYSTEM_LISTS if p.is_file()), None)
    if not wordlist or not wordlist.is_file():
        parser.error("no word list found: pass --wordlist FILE (one word per line)")
    known = load_words(wordlist)
    for extra in args.allow:
        if not extra.is_file():
            parser.error(f"not a file: {extra}")
        known |= load_words(extra)
    known_sorted = sorted(known)

    total = 0
    for path in args.files:
        if not path.is_file():
            print(f"not found: {path}", file=sys.stderr)
            total += 1
            continue
        unknown = find_unknown(path.read_text(encoding="utf-8", errors="replace"), known,
                               args.ignore_capitalized)
        print(f"{path.name}: {len(unknown)} unknown word(s)")
        for word, lines in sorted(unknown.items(), key=lambda item: item[1][0]):
            hints = suggest(word, known_sorted)
            where = ", ".join(map(str, lines[:4])) + ("..." if len(lines) > 4 else "")
            advice = f" did you mean: {', '.join(hints)}" if hints else ""
            print(f"  {word:<14} line {where:<8}{advice}".rstrip())
        total += len(unknown)
    print(f"\n{total} word(s) to check against {wordlist.name} ({len(known):,} known words).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
