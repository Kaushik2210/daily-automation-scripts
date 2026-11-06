"""Generate placeholder text: paragraphs, sentences or a fixed number of words."""
import argparse
import random
import sys

WORDS = [
    "lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed",
    "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna",
    "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud", "exercitation", "ullamco",
    "laboris", "nisi", "aliquip", "ex", "ea", "commodo", "consequat", "duis", "aute", "irure",
    "in", "reprehenderit", "voluptate", "velit", "esse", "cillum", "eu", "fugiat", "nulla",
    "pariatur", "excepteur", "sint", "occaecat", "cupidatat", "non", "proident", "sunt",
    "culpa", "qui", "officia", "deserunt", "mollit", "anim", "id", "est", "laborum",
]
OPENING = "Lorem ipsum dolor sit amet, consectetur adipiscing elit"


def sentence(rng, min_words=6, max_words=14):
    words = [rng.choice(WORDS) for _ in range(rng.randint(min_words, max_words))]
    if len(words) > 8:  # a comma in longer sentences reads more naturally
        words[rng.randint(3, len(words) - 3)] += ","
    return " ".join(words).capitalize() + "."


def paragraph(rng, sentences=5):
    return " ".join(sentence(rng) for _ in range(sentences))


def generate(paragraphs=3, sentences=5, seed=None, classic_start=True):
    rng = random.Random(seed)
    result = [paragraph(rng, sentences) for _ in range(paragraphs)]
    if classic_start and result:
        first, _, rest = result[0].partition(". ")
        result[0] = f"{OPENING}. {rest}" if rest else f"{OPENING}."
    return result


def words(count, seed=None):
    rng = random.Random(seed)
    return " ".join(rng.choice(WORDS) for _ in range(count))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate placeholder text.")
    parser.add_argument("-p", "--paragraphs", type=int, default=3, help="number of paragraphs")
    parser.add_argument("-s", "--sentences", type=int, default=5, help="sentences per paragraph")
    parser.add_argument("-w", "--words", type=int, help="print exactly this many words instead")
    parser.add_argument("--seed", type=int, help="seed for repeatable output")
    parser.add_argument("--no-classic-start", action="store_true",
                        help="don't begin with 'Lorem ipsum dolor sit amet'")
    args = parser.parse_args(argv)
    if min(args.paragraphs, args.sentences) < 1 or (args.words is not None and args.words < 1):
        parser.error("counts must be at least 1")

    if args.words:
        print(words(args.words, args.seed))
    else:
        print("\n\n".join(generate(args.paragraphs, args.sentences, args.seed,
                                   not args.no_classic_start)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
