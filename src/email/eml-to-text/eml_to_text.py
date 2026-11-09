"""Convert .eml email files to plain text (printed, or saved with --apply)."""
import argparse
import email
import email.policy
import sys
import textwrap
from html.parser import HTMLParser
from pathlib import Path

BLOCKS = {"p", "div", "br", "tr", "table", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
          "blockquote", "section", "article", "li"}
SKIPPED = {"script", "style", "head", "title"}


class HtmlToText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip, self._href = [], 0, ""

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED:
            self._skip += 1
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCKS:
            self.parts.append("\n")
        elif tag == "a":
            self._href = dict(attrs).get("href") or ""

    def handle_endtag(self, tag):
        if tag in SKIPPED and self._skip:
            self._skip -= 1
        elif tag in BLOCKS and tag != "li":
            self.parts.append("\n")
        elif tag == "a":
            if self._href.startswith(("http://", "https://")):
                self.parts.append(f" ({self._href})")
            self._href = ""

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html):
    parser = HtmlToText()
    parser.feed(html)
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def body_text(msg):
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        content = part.get_content()
    except (LookupError, ValueError):
        return ""
    return html_to_text(content) if part.get_content_subtype() == "html" else content.strip()


def convert(raw, width=0):
    """Turn raw .eml bytes into readable text: header lines, body and an attachment list."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    head = [f"{label}: {msg[label]}" for label in ("From", "To", "Cc", "Date", "Subject")
            if msg[label]]
    body = body_text(msg)
    if width:
        body = "\n".join(textwrap.fill(line, width, subsequent_indent="  " * line.startswith("- "))
                         for line in body.splitlines())
    files = [part.get_filename() for part in msg.walk() if part.get_filename()]
    out = "\n".join(head) + "\n\n" + (body or "(no text in this message)")
    if files:
        out += "\n\nAttachments: " + ", ".join(files)
    return out + "\n"


def find_emls(paths):
    found = []
    for path in paths:
        if path.is_dir():
            found += sorted(path.rglob("*.eml"))
        else:
            found.append(path)
    return found


def free_path(folder, name):
    target, count = folder / name, 1
    while target.exists():
        count += 1
        target = folder / f"{Path(name).stem}-{count}{Path(name).suffix}"
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert .eml files to plain text.")
    parser.add_argument("paths", nargs="+", type=Path, help=".eml files or folders of them")
    parser.add_argument("--width", type=int, default=0, help="wrap the body at this width")
    parser.add_argument("--out-dir", type=Path, help="write one .txt per message here")
    parser.add_argument("--apply", action="store_true", help="actually write the .txt files")
    args = parser.parse_args(argv)

    files = find_emls(args.paths)
    if not files:
        print("No .eml files found.")
        return 1
    failed = 0
    for path in files:
        try:
            text = convert(path.read_bytes(), args.width)
        except OSError as err:
            print(f"{path}: couldn't read ({err.strerror or err})")
            failed += 1
            continue
        if not args.out_dir:
            print(f"===== {path.name} =====\n{text}" if len(files) > 1 else text, end="")
            continue
        target = free_path(args.out_dir, path.stem + ".txt")
        if not args.apply:
            print(f"would write {target}")
            continue
        args.out_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target}")
    if args.out_dir and not args.apply:
        print("Dry run - nothing written. Add --apply to create the .txt files.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
