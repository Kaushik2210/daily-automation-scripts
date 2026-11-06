"""Pull plain text (or simple markdown) out of Word .docx files without Word."""
import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_XML_BYTES = 30 * 1024 * 1024


def paragraph_text(paragraph):
    parts = []
    for node in paragraph.iter():
        if node.tag == f"{NS}t":
            parts.append(node.text or "")
        elif node.tag == f"{NS}tab":
            parts.append("\t")
        elif node.tag == f"{NS}br":
            parts.append("\n")
    return "".join(parts)


def paragraph_style(paragraph):
    style = paragraph.find(f"{NS}pPr/{NS}pStyle")
    return (style.get(f"{NS}val") if style is not None else "") or ""


def read_blocks(path):
    """Return a list of (kind, text) for the document body: title/h1.., li, p, table."""
    with zipfile.ZipFile(path) as archive:
        info = archive.getinfo("word/document.xml")
        if info.file_size > MAX_XML_BYTES:
            raise ValueError("document is too large to read safely")
        root = ET.fromstring(archive.read("word/document.xml"))
    blocks = []
    for element in root.find(f"{NS}body"):
        if element.tag == f"{NS}p":
            text = paragraph_text(element)
            style = paragraph_style(element).lower()
            if not text.strip():
                continue
            if style == "title":
                blocks.append(("h0", text))
            elif style.startswith("heading"):
                level = "".join(ch for ch in style if ch.isdigit()) or "1"
                blocks.append((f"h{level}", text))
            elif "list" in style:
                blocks.append(("li", text))
            else:
                blocks.append(("p", text))
        elif element.tag == f"{NS}tbl":
            rows = [[" ".join(paragraph_text(p) for p in cell.iter(f"{NS}p")).strip()
                     for cell in row.findall(f"{NS}tc")] for row in element.iter(f"{NS}tr")]
            blocks.append(("table", rows))
    return blocks


def render(blocks, markdown=False):
    lines = []
    for kind, content in blocks:
        if kind == "table":
            for number, row in enumerate(content):
                lines.append("| " + " | ".join(row) + " |" if markdown else "\t".join(row))
                if markdown and number == 0:
                    lines.append("|" + " --- |" * len(row))
        elif kind == "li":
            lines.append(f"- {content}" if markdown else f"* {content}")
        elif kind.startswith("h") and markdown:
            lines.append(f"{'#' * max(int(kind[1]), 1)} {content}")
        else:
            lines.append(content)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract text from .docx files.")
    parser.add_argument("files", nargs="+", type=Path, help=".docx files")
    parser.add_argument("--markdown", action="store_true",
                        help="keep headings, bullets and tables as markdown")
    parser.add_argument("-o", "--outdir", type=Path, help="folder for the output files")
    parser.add_argument("--apply", action="store_true",
                        help="really write the files (default only prints the text)")
    args = parser.parse_args(argv)

    status = 0
    for path in args.files:
        try:
            text = render(read_blocks(path), args.markdown)
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError, ValueError) as err:
            print(f"{path.name}: can't read it as a Word document ({err})", file=sys.stderr)
            status = 1
            continue
        print(f"== {path.name}: {len(text.split())} word(s)")
        if args.apply:
            extension = ".md" if args.markdown else ".txt"
            target = (args.outdir or path.parent) / f"{path.stem}{extension}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            print(f"wrote {target}")
        else:
            print(text, end="")
    if status == 0 and not args.apply:
        print("\nPreview only. Use --apply to save the text to files.")
    return status


if __name__ == "__main__":
    sys.exit(main())
