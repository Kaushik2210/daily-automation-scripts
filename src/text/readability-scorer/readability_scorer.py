"""Score how easy a text is to read: Flesch reading ease, grade levels and more."""
import argparse
import math
import re
import sys
from pathlib import Path

LEVELS = [(90, "very easy (about 5th grade)"), (80, "easy (6th grade)"),
          (70, "fairly easy (7th grade)"), (60, "plain English (8th-9th grade)"),
          (50, "fairly difficult (10th-12th grade)"), (30, "difficult (college)"),
          (-math.inf, "very difficult (graduate level)")]


def count_syllables(word):
    """A good-enough English syllable estimate."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,3}", word)))


def analyse(text):
    """Return a dict of counts and readability scores (or None if there are no words)."""
    sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text.strip()) if re.search(r"\w", s)]
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    if not words or not sentences:
        return None
    syllables = [count_syllables(w) for w in words]
    letters = sum(len(re.sub(r"[^A-Za-z]", "", w)) for w in words)
    n_words, n_sent = len(words), len(sentences)
    complex_words = sum(1 for s in syllables if s >= 3)
    per_sentence, per_word = n_words / n_sent, sum(syllables) / n_words
    ease = 206.835 - 1.015 * per_sentence - 84.6 * per_word
    grades = {
        "Flesch-Kincaid": 0.39 * per_sentence + 11.8 * per_word - 15.59,
        "Gunning fog": 0.4 * (per_sentence + 100 * complex_words / n_words),
        "Coleman-Liau": (0.0588 * (100 * letters / n_words) - 0.296 * (100 * n_sent / n_words)
                         - 15.8),
        "SMOG": 1.043 * math.sqrt(complex_words * 30 / n_sent) + 3.1291,
        "ARI": 4.71 * letters / n_words + 0.5 * per_sentence - 21.43,
    }
    return {"words": n_words, "sentences": n_sent, "per_sentence": per_sentence,
            "ease": ease, "grades": grades, "grade": sum(grades.values()) / len(grades),
            "complex_percent": 100 * complex_words / n_words}


def describe(ease):
    return next(label for floor, label in LEVELS if ease >= floor)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score the readability of text files.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--target-grade", type=float,
                        help="exit with 1 if any file's average grade is above this")
    args = parser.parse_args(argv)

    too_hard = failed = 0
    for path in args.files:
        if not path.is_file():
            print(f"not found: {path}", file=sys.stderr)
            failed += 1
            continue
        result = analyse(path.read_text(encoding="utf-8", errors="replace"))
        if result is None:
            print(f"{path.name}: no text to score")
            failed += 1
            continue
        print(f"{path.name}: {result['words']} words, {result['sentences']} sentences "
              f"({result['per_sentence']:.1f} words each, "
              f"{result['complex_percent']:.0f}% long words)")
        print(f"  Reading ease   {result['ease']:5.1f}  {describe(result['ease'])}")
        for name, value in result["grades"].items():
            print(f"  {name:<14} grade {max(value, 0):4.1f}")
        print(f"  Average grade  {max(result['grade'], 0):4.1f}")
        if args.target_grade is not None and result["grade"] > args.target_grade:
            print(f"  Too hard: above the target of grade {args.target_grade:g}")
            too_hard += 1
    return 1 if too_hard or failed else 0


if __name__ == "__main__":
    sys.exit(main())
