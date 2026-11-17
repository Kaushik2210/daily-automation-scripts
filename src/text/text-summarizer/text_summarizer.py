"""Make an extractive summary: pick the most important sentences of a long text."""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

STOPWORDS = {
    "a", "about", "above", "after", "again", "all", "also", "am", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "him", "his", "how",
    "however", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "many", "me", "more",
    "most", "much", "my", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or",
    "other", "our", "out", "over", "own", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "will", "with", "would", "you", "your",
}
ABBREVIATIONS = ("mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "no")


def split_sentences(paragraph):
    """Split on . ! ? followed by a capital letter, without cutting after abbreviations."""
    pieces, start = [], 0
    for match in re.finditer(r"[.!?][\"')\]]*\s+(?=[A-Z0-9\"'(])", paragraph):
        before = paragraph[start:match.start()].split()[-1:] or [""]
        if before[0].rstrip(".").lower() in ABBREVIATIONS:
            continue
        pieces.append(paragraph[start:match.end()].strip())
        start = match.end()
    tail = paragraph[start:].strip()
    return pieces + ([tail] if tail else [])


def words_of(sentence):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z'-]+", sentence.lower()) if w not in STOPWORDS]


def summarise(text, count=3):
    """Return the `count` best sentences, in their original order."""
    sentences = []  # (index, text, is first of its paragraph)
    for paragraph in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        for position, sentence in enumerate(split_sentences(" ".join(paragraph.split()))):
            sentences.append((len(sentences), sentence, position == 0))
    frequency = Counter(w for _, s, _ in sentences for w in words_of(s))
    scored = []
    for index, sentence, first in sentences:
        words = words_of(sentence)
        if len(words) < 4:
            continue
        score = sum(frequency[w] for w in words) / (len(words) ** 0.6)
        scored.append((score * (1.25 if first else 1.0), index, sentence))
    best = sorted(scored, reverse=True)[:count]
    return [s for _, _, s in sorted(best, key=lambda item: item[1])], len(sentences)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarise a text file by picking key sentences.")
    parser.add_argument("file", type=Path)
    parser.add_argument("-n", "--sentences", type=int, default=3, help="sentences to keep (3)")
    parser.add_argument("--bullets", action="store_true", help="one bullet per sentence")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")
    if args.sentences < 1:
        parser.error("--sentences must be at least 1")

    text = args.file.read_text(encoding="utf-8", errors="replace")
    summary, total = summarise(text, args.sentences)
    if not summary:
        print("The text is too short to summarise.", file=sys.stderr)
        return 1
    print("\n".join(f"- {s}" for s in summary) if args.bullets else " ".join(summary))
    kept = sum(len(s.split()) for s in summary)
    original = len(text.split())
    print(f"\nKept {len(summary)} of {total} sentence(s): {kept} of {original} words "
          f"({100 * kept // max(original, 1)}%).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
