from markdown_toc_generator import build_toc, find_headings, insert_toc, main

DOC = """# Title

## Install

Some text.

```bash
# not a heading
```

## Usage

### Options

## Usage
"""


def test_headings_skip_code_blocks_and_dedupe_anchors():
    headings = find_headings(DOC)
    assert [h[1] for h in headings] == ["Title", "Install", "Usage", "Options", "Usage"]
    assert headings[-1][2] == "usage-1"


def test_build_toc_levels_and_indent():
    toc = build_toc(find_headings(DOC))
    assert toc.splitlines() == [
        "- [Install](#install)",
        "- [Usage](#usage)",
        "  - [Options](#options)",
        "- [Usage](#usage-1)",
    ]


def test_insert_after_first_heading_then_replace():
    toc = build_toc(find_headings(DOC))
    once = insert_toc(DOC, toc)
    assert once.splitlines()[2] == "<!-- TOC -->"
    twice = insert_toc(once, "- [New](#new)")
    assert "- [New](#new)" in twice and "- [Install](#install)" not in twice
    assert twice.count("<!-- TOC -->") == 1


def test_cli_dry_run_and_apply(tmp_path, capsys):
    f = tmp_path / "doc.md"
    f.write_text(DOC)
    main([str(f)])
    assert f.read_text() == DOC
    main([str(f), "--apply"])
    assert "<!-- TOC -->" in f.read_text()
