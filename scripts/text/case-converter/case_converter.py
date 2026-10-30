"""Convert text between camelCase, snake_case, kebab-case, Title Case and more."""
import argparse
import re
import sys

WORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")

STYLES = {
    "snake": lambda w: "_".join(x.lower() for x in w),
    "kebab": lambda w: "-".join(x.lower() for x in w),
    "constant": lambda w: "_".join(x.upper() for x in w),
    "camel": lambda w: "".join(x.lower() if i == 0 else x.capitalize() for i, x in enumerate(w)),
    "pascal": lambda w: "".join(x.capitalize() for x in w),
    "title": lambda w: " ".join(x.capitalize() for x in w),
    "sentence": lambda w: " ".join(x.lower() if i else x.capitalize() for i, x in enumerate(w)),
    "lower": lambda w: " ".join(x.lower() for x in w),
    "upper": lambda w: " ".join(x.upper() for x in w),
}


def split_words(text):
    """Split camelCase, snake_case, kebab-case or spaced text into words."""
    return WORD_RE.findall(text)


def convert(text, style):
    return STYLES[style](split_words(text))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert text between naming styles.")
    parser.add_argument("text", nargs="*", help="text to convert (default: read lines from stdin)")
    parser.add_argument("--to", dest="style", required=True, choices=sorted(STYLES),
                        help="target style")
    args = parser.parse_args(argv)

    lines = args.text or sys.stdin.read().splitlines()
    for line in lines:
        print(convert(line, args.style))
    return 0


if __name__ == "__main__":
    sys.exit(main())
