"""Turn titles and phrases into clean, URL-safe slugs."""
import argparse
import re
import sys
import unicodedata


def slugify(text, sep="-", max_length=0, keep_case=False):
    """Return a slug: accents removed, punctuation dropped, words joined by `sep`."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    if not keep_case:
        plain = plain.lower()
    plain = plain.replace("&", " and ")
    words = re.findall(r"[A-Za-z0-9]+", plain)
    slug = sep.join(words)
    if max_length and len(slug) > max_length:
        slug = slug[:max_length]
        if sep in slug:  # don't cut a word in half
            slug = slug.rsplit(sep, 1)[0]
        slug = slug.strip(sep)
    return slug


def unique_slugs(titles, **options):
    """Slugify many titles, adding -2, -3 ... to repeats."""
    seen, result = {}, []
    for title in titles:
        slug = slugify(title, **options)
        seen[slug] = seen.get(slug, 0) + 1
        result.append(slug if seen[slug] == 1 else f"{slug}{options.get('sep', '-')}{seen[slug]}")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make URL-safe slugs from text.")
    parser.add_argument("text", nargs="*", help="titles to convert (default: lines from stdin)")
    parser.add_argument("--sep", default="-", help="word separator (default: -)")
    parser.add_argument("--max-length", type=int, default=0, help="shorten to this many characters")
    parser.add_argument("--keep-case", action="store_true", help="don't lowercase")
    args = parser.parse_args(argv)

    titles = args.text or sys.stdin.read().splitlines()
    for slug in unique_slugs(titles, sep=args.sep, max_length=args.max_length,
                             keep_case=args.keep_case):
        print(slug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
