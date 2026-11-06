"""Turn a markdown file into a clean, readable PDF."""
import argparse
import re
import sys
from pathlib import Path

from fpdf import FPDF

REPLACEMENTS = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                "—": "-", "…": "...", "•": "-", " ": " "}
SIZES = {1: 22, 2: 17, 3: 14, 4: 12}


def clean(text):
    """Strip inline markdown and make the text safe for the built-in PDF fonts (Latin-1)."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)      # images -> alt text
    text = re.sub(r"\[([^\]]+)\]\(([^)]*)\)", r"\1 (\2)", text)  # links -> text (url)
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])[*_](.+?)[*_](?![\w*])", r"\1", text)
    text = text.replace("`", "")
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def parse_markdown(text):
    """Return a list of (kind, text) blocks: h1-h4, p, li, code, rule."""
    blocks, paragraph, in_code, code = [], [], False, []

    def flush():
        if paragraph:
            blocks.append(("p", " ".join(paragraph)))
            paragraph.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                blocks.append(("code", "\n".join(code)))
                code.clear()
            else:
                flush()
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif re.match(r"^\s*(-{3,}|\*{3,})\s*$", line):
            flush()
            blocks.append(("rule", ""))
        elif match := re.match(r"^(#{1,6})\s+(.*)$", line):
            flush()
            blocks.append((f"h{min(len(match.group(1)), 4)}", match.group(2).strip()))
        elif match := re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", line):
            flush()
            blocks.append(("li", match.group(1).strip()))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    if code:
        blocks.append(("code", "\n".join(code)))
    return blocks


def render(markdown_text):
    """Return (pdf_bytes, page_count, block_count) for the markdown text."""
    blocks = parse_markdown(markdown_text)
    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()
    for kind, text in blocks:
        text = clean(text)
        if kind.startswith("h"):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", SIZES[int(kind[1])])
            pdf.multi_cell(0, SIZES[int(kind[1])] * 0.55, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif kind == "li":
            pdf.set_font("Helvetica", "", 11)
            pdf.set_x(26)
            pdf.multi_cell(0, 6, "- " + text, new_x="LMARGIN", new_y="NEXT")
        elif kind == "code":
            pdf.set_font("Courier", "", 9)
            pdf.set_fill_color(240, 240, 240)
            pdf.multi_cell(0, 5, text, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif kind == "rule":
            pdf.ln(2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(4)
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    return bytes(pdf.output()), pdf.page_no(), len(blocks)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert markdown to PDF.")
    parser.add_argument("file", type=Path, help="markdown file")
    parser.add_argument("-o", "--output", type=Path, help="result file (default: <name>.pdf)")
    parser.add_argument("--apply", action="store_true",
                        help="really write the PDF (default is a dry run)")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        parser.error(f"not a file: {args.file}")

    data, pages, blocks = render(args.file.read_text(encoding="utf-8-sig"))
    target = args.output or args.file.with_suffix(".pdf")
    print(f"{args.file.name}: {blocks} block(s) -> {pages} page(s), {len(data)} bytes")
    if not args.apply:
        print(f"Dry run: would write {target}. Use --apply to do it.")
        return 0
    if target.exists():
        print(f"{target} already exists; choose another name with -o.", file=sys.stderr)
        return 1
    target.write_bytes(data)
    print(f"Wrote {target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
