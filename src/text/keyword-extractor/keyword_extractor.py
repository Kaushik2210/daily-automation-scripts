"""Pull the top keywords (and optionally two-word phrases) out of one or more documents."""
import argparse
import math
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
EXTENSIONS = {".txt", ".md", ".markdown", ".rst"}


def tokens(text):
    return [w for w in re.findall(r"[a-z][a-z'-]{2,}", text.lower()) if w not in STOPWORDS]


def phrases(text):
    """Pairs of neighbouring content words (not split by punctuation or stopwords)."""
    pairs = []
    for chunk in re.split(r"[.,;:!?()\n]+", text.lower()):
        words = re.findall(r"[a-z][a-z'-]*", chunk)
        for first, second in zip(words, words[1:], strict=False):
            if (first not in STOPWORDS and second not in STOPWORDS
                    and len(first) > 2 and len(second) > 2):
                pairs.append(f"{first} {second}")
    return pairs


def rank(documents, top, use_phrases):
    """documents: {name: text}. Return {name: [(keyword, score, count)]}."""
    counts = {name: Counter(phrases(text) if use_phrases else tokens(text))
              for name, text in documents.items()}
    if use_phrases:  # a phrase that appears only once is rarely a keyword
        counts = {name: Counter({k: v for k, v in c.items() if v > 1}) or c
                  for name, c in counts.items()}
    n = len(documents)
    containing = Counter(term for c in counts.values() for term in c)
    result = {}
    for name, counter in counts.items():
        total = sum(counter.values()) or 1
        scored = []
        for term, count in counter.items():
            idf = math.log((1 + n) / (1 + containing[term])) + 1 if n > 1 else 1.0
            scored.append((term, count / total * idf, count))
        scored.sort(key=lambda item: (-item[1], item[0]))
        result[name] = scored[:top]
    return result


def collect(paths):
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in EXTENSIONS)
        elif path.is_file():
            files.append(path)
        else:
            print(f"not found: {path}", file=sys.stderr)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract keywords from documents.")
    parser.add_argument("paths", nargs="+", type=Path, help="text/markdown files or folders")
    parser.add_argument("--top", type=int, default=8, help="keywords per document (8)")
    parser.add_argument("--phrases", action="store_true", help="find two-word phrases instead")
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")

    files = collect(args.paths)
    documents = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in files}
    if not documents:
        print("No documents found.", file=sys.stderr)
        return 1
    ranked = rank(documents, args.top, args.phrases)
    for name, keywords in ranked.items():
        print(f"{name}  ({len(documents[name].split())} words)")
        if not keywords:
            print("    (no keywords)")
        for term, _score, count in keywords:
            print(f"    {term:<24} x{count}")
    if len(documents) > 1:
        print("\nKeywords are weighted so that words found in every document rank lower.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
