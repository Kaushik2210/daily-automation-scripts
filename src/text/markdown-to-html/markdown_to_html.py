"""Convert a markdown file into a single, styled, self-contained HTML page."""
import argparse
import html
import re
import sys
from pathlib import Path

CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--code:#f6f8fa;
--link:#0969da}@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;
--line:#30363d;--code:#161b22;--link:#4493f8}}
body{max-width:46rem;margin:2rem auto;padding:0 1rem;background:var(--bg);color:var(--fg);
font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}
h1,h2{border-bottom:1px solid var(--line);padding-bottom:.3em}a{color:var(--link)}
code{background:var(--code);padding:.15em .35em;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:1rem;border-radius:6px;overflow:auto}pre code{padding:0}
blockquote{margin:0;padding:0 1rem;border-left:4px solid var(--line);color:var(--muted)}
table{border-collapse:collapse}td,th{border:1px solid var(--line);padding:.4rem .7rem}
img{max-width:100%}hr{border:0;border-top:1px solid var(--line)}
"""
ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def inline(text):
    """Escape HTML, then turn markdown inline syntax into tags."""
    codes = []

    def keep(match):
        codes.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__",
                  lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)|(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])",
                  lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def convert(markdown):
    """Return (html body, title or None)."""
    lines, out, title, i = markdown.replace("\r\n", "\n").split("\n"), [], None, 0
    paragraph = []

    def flush():
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush()
            language, code = line.strip()[3:].strip(), []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            attr = f' class="language-{html.escape(language)}"' if language else ""
            out.append(f"<pre><code{attr}>{html.escape(chr(10).join(code))}</code></pre>")
        elif re.match(r"^#{1,6}\s", line):
            flush()
            level = len(line) - len(line.lstrip("#"))
            text = line[level:].strip().rstrip("#").strip()
            title = title or (text if level == 1 else None)
            slug = re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")
            out.append(f'<h{level} id="{slug}">{inline(text)}</h{level}>')
        elif re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", line):
            flush()
            out.append("<hr>")
        elif line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{convert(chr(10).join(quote))[0]}</blockquote>")
            continue
        elif "|" in line and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1]):
            flush()
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(cells(lines[i]))
                i += 1
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                           for row in rows)
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + f"</tr></thead><tbody>{body}</tbody></table>")
            continue
        elif ITEM.match(line):
            flush()
            ordered = line.lstrip()[0].isdigit()
            items = []
            while i < len(lines) and ITEM.match(lines[i]):
                items.append(ITEM.match(lines[i]).group(3))
                i += 1
            tag = "ol" if ordered else "ul"
            rendered = []
            for item in items:
                task = re.match(r"\[([ xX])\]\s+(.*)", item)
                if task:
                    box = "checked " if task.group(1).lower() == "x" else ""
                    rendered.append(
                        f'<li><input type="checkbox" disabled {box}> {inline(task.group(2))}</li>')
                else:
                    rendered.append(f"<li>{inline(item)}</li>")
            out.append(f"<{tag}>{''.join(rendered)}</{tag}>")
            continue
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
        i += 1
    flush()
    return "\n".join(out), title


def page(body, title, styled=True):
    style = f"<style>{CSS}</style>" if styled else ""
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{html.escape(title)}</title>\n{style}\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert markdown to an HTML page.")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="HTML file to create (next to the input)")
    parser.add_argument("--title", help="page title (default: the first # heading)")
    parser.add_argument("--no-style", action="store_true", help="leave out the built-in CSS")
    parser.add_argument("--apply", action="store_true",
                        help="really write the file (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.markdown.is_file():
        parser.error(f"not a file: {args.markdown}")

    body, found = convert(args.markdown.read_text(encoding="utf-8", errors="replace"))
    title = args.title or found or args.markdown.stem
    output = args.output or args.markdown.with_suffix(".html")
    document = page(body, title, not args.no_style)
    print(f"{args.markdown.name} -> {output.name}: \"{title}\", {len(document):,} characters, "
          f"{body.count('<h') - body.count('<hr')} heading(s)")
    if not args.apply:
        print("Dry run. Use --apply to write the file.")
        return 0
    if output.exists():
        print(f"{output} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    output.write_text(document, encoding="utf-8")
    print(f"Saved {output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
