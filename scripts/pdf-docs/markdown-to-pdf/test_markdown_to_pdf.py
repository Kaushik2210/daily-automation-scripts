import markdown_to_pdf as mp

DOC = """# Title

Intro with **bold**, *italic*, `code` and a [link](https://example.com).

## List

- first item
- second item
1. numbered

```python
print("hi")
```

---

Curly “quotes” — and a snowman ☃.
"""


def test_clean_strips_inline_markup_and_unsafe_characters():
    assert mp.clean("**bold** and *italic* and `code`") == "bold and italic and code"
    assert mp.clean("[site](https://x.test)") == "site (https://x.test)"
    assert mp.clean("“quoted” — ok") == '"quoted" - ok'
    assert mp.clean("snow ☃ man") == "snow ? man"


def test_parse_markdown_blocks():
    kinds = [kind for kind, _ in mp.parse_markdown(DOC)]
    assert kinds == ["h1", "p", "h2", "li", "li", "li", "code", "rule", "p"]
    blocks = dict(mp.parse_markdown("# Hello\n\ntext one\ntext two\n"))
    assert blocks["p"] == "text one text two"


def test_unclosed_code_fence_is_kept():
    assert mp.parse_markdown("```\nnever closed")[-1] == ("code", "never closed")


def test_render_makes_a_valid_pdf_with_pages():
    data, pages, blocks = mp.render(DOC)
    assert data.startswith(b"%PDF") and data.rstrip().endswith(b"%%EOF")
    assert pages == 1 and blocks == 9
    long_doc = "\n\n".join(f"Paragraph number {i} " + "word " * 80 for i in range(40))
    assert mp.render(long_doc)[1] > 1


def test_cli_dry_run_apply_and_no_overwrite(tmp_path, capsys):
    src = tmp_path / "notes.md"
    src.write_text(DOC, encoding="utf-8")
    assert mp.main([str(src)]) == 0 and not (tmp_path / "notes.pdf").exists()
    assert "1 page(s)" in capsys.readouterr().out
    assert mp.main([str(src), "--apply"]) == 0
    assert (tmp_path / "notes.pdf").read_bytes().startswith(b"%PDF")
    assert mp.main([str(src), "--apply"]) == 1
