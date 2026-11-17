"""Convert Word (.docx) files to markdown: headings, bold/italic, links, lists and tables."""
import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_XML_BYTES = 30 * 1024 * 1024


def read_part(archive, name):
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_XML_BYTES:
        raise ValueError(f"{name} is too large to read safely")
    return ET.fromstring(archive.read(name))


def load(path):
    """Return (document body element, {rId: url}, {numId: numbering format})."""
    with zipfile.ZipFile(path) as archive:
        document = read_part(archive, "word/document.xml")
        if document is None:
            raise ValueError("not a Word document (no word/document.xml)")
        links, formats = {}, {}
        rels = read_part(archive, "word/_rels/document.xml.rels")
        for rel in rels if rels is not None else []:
            if rel.get("Type", "").endswith("/hyperlink"):
                links[rel.get("Id")] = rel.get("Target")
        numbering = read_part(archive, "word/numbering.xml")
        if numbering is not None:
            abstract = {a.get(f"{W}abstractNumId"): a.find(f"{W}lvl/{W}numFmt")
                        for a in numbering.findall(f"{W}abstractNum")}
            for num in numbering.findall(f"{W}num"):
                ref = num.find(f"{W}abstractNumId")
                fmt = abstract.get(ref.get(f"{W}val")) if ref is not None else None
                formats[num.get(f"{W}numId")] = fmt.get(f"{W}val") if fmt is not None else "bullet"
    return document.find(f"{W}body"), links, formats


def is_on(props, name):
    node = props.find(f"{W}{name}") if props is not None else None
    return node is not None and node.get(f"{W}val") not in ("0", "false")


def run_text(run):
    pieces = []
    for node in run:
        if node.tag == f"{W}t":
            pieces.append(node.text or "")
        elif node.tag == f"{W}tab":
            pieces.append("\t")
        elif node.tag == f"{W}br":
            pieces.append("\n")
    return "".join(pieces)


def run_parts(paragraph, links):
    """Yield (text, bold, italic, url) for each piece of a paragraph."""
    for child in paragraph:
        url, runs = None, []
        if child.tag == f"{W}r":
            runs = [child]
        elif child.tag == f"{W}hyperlink":
            url, runs = links.get(child.get(f"{R}id")), child.findall(f"{W}r")
        for run in runs:
            props = run.find(f"{W}rPr")
            text = run_text(run)
            if text:
                yield text, is_on(props, "b"), is_on(props, "i"), url


def wrap(text, bold, italic):
    """Put markdown markers around text but keep leading/trailing spaces outside them."""
    stripped = text.strip()
    if not stripped:
        return text
    lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    mark = ("**" if bold else "") + ("*" if italic else "")
    return f"{lead}{mark}{stripped}{mark[::-1]}{trail}"


def inline(paragraph, links):
    pieces = []  # merge neighbouring runs with the same look so we don't emit **a****b**
    for text, bold, italic, url in run_parts(paragraph, links):
        if pieces and pieces[-1][1:] == (bold, italic, url):
            pieces[-1] = (pieces[-1][0] + text, bold, italic, url)
        else:
            pieces.append((text, bold, italic, url))
    out = []
    for text, bold, italic, url in pieces:
        formatted = wrap(text, bold, italic)
        out.append(f"[{formatted.strip()}]({url})" if url else formatted)
    return "".join(out).replace("\n", "  \n").strip()


def style_of(paragraph):
    node = paragraph.find(f"{W}pPr/{W}pStyle")
    return (node.get(f"{W}val") if node is not None else "").lower()


def list_item(paragraph, text, formats, counters):
    """Return a markdown list line for a list paragraph, or None if it isn't one."""
    num, style = paragraph.find(f"{W}pPr/{W}numPr"), style_of(paragraph)
    if num is None and "list" not in style:
        return None
    level_node = num.find(f"{W}ilvl") if num is not None else None
    id_node = num.find(f"{W}numId") if num is not None else None
    level = int(level_node.get(f"{W}val")) if level_node is not None else 0
    kind = formats.get(id_node.get(f"{W}val")) if id_node is not None else None
    ordered = kind != "bullet" if kind else "number" in style
    key = (id_node.get(f"{W}val") if id_node is not None else style, level)
    counters[key] = counters.get(key, 0) + 1
    marker = f"{counters[key]}." if ordered else "-"
    return f"{'  ' * level}{marker} {text}"


def table_lines(table, links):
    rows = []
    for row in table.iter(f"{W}tr"):
        cells = [" ".join(inline(p, links) for p in cell.iter(f"{W}p"))
                 for cell in row.findall(f"{W}tc")]
        rows.append([cell.replace("|", "\\|").strip() for cell in cells])
    if not rows:
        return []
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    return (["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
            + ["| " + " | ".join(row) + " |" for row in rows[1:]])


def convert(path):
    body, links, formats = load(path)
    has_title = any(style_of(p) == "title" for p in body.findall(f"{W}p"))
    blocks, counters = [], {}  # (kind, text); consecutive "li" blocks stay together
    for element in body:
        if element.tag == f"{W}tbl":
            blocks.append(("table", "\n".join(table_lines(element, links))))
            counters.clear()
            continue
        if element.tag != f"{W}p":
            continue
        text = inline(element, links)
        if not text:
            continue
        style = style_of(element)
        item = list_item(element, text, formats, counters)
        if item is not None:
            blocks.append(("li", item))
            continue
        counters.clear()
        if style == "title":
            blocks.append(("p", f"# {text}"))
        elif style.startswith("heading") and style[7:].isdigit():
            level = min(int(style[7:]) + (1 if has_title else 0), 6)
            blocks.append(("p", f"{'#' * level} {text}"))
        else:
            blocks.append(("p", text))
    out = []
    for number, (kind, text) in enumerate(blocks):
        if number and not (kind == "li" and blocks[number - 1][0] == "li"):
            out.append("")
        out.append(text)
    return "\n".join(out).strip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert .docx files to markdown.")
    parser.add_argument("docx", nargs="+", type=Path, help="Word documents")
    parser.add_argument("-o", "--outdir", type=Path,
                        help="write FILE.md files into this folder instead of printing")
    args = parser.parse_args(argv)

    failures = 0
    for path in args.docx:
        try:
            markdown = convert(path)
        except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as err:
            print(f"{path.name}: can't read it ({err})", file=sys.stderr)
            failures += 1
            continue
        if not args.outdir:
            if len(args.docx) > 1:
                print(f"<!-- {path.name} -->")
            print(markdown, end="")
            continue
        target = args.outdir / f"{path.stem}.md"
        if target.exists():
            print(f"skip {path.name}: {target} already exists")
            continue
        args.outdir.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        print(f"{path.name} -> {target} ({len(markdown.splitlines())} lines)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
