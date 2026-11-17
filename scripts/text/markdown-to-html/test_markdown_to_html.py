import markdown_to_html as m2h


def body(markdown):
    return m2h.convert(markdown)[0]


def test_inline_formatting_and_escaping():
    out = m2h.inline("**bold** *it* `a<b` [x](http://e.com) ~~old~~ <script>")
    assert "<strong>bold</strong>" in out and "<em>it</em>" in out
    assert "<code>a&lt;b</code>" in out and '<a href="http://e.com">x</a>' in out
    assert "<del>old</del>" in out and "&lt;script&gt;" in out and "<script>" not in out


def test_code_is_not_formatted_inside():
    assert m2h.inline("`**not bold**`") == "<code>**not bold**</code>"


def test_headings_and_title():
    html_body, title = m2h.convert("# Hello World\n\n## Part two!\n")
    assert title == "Hello World"
    assert '<h1 id="hello-world">Hello World</h1>' in html_body
    assert '<h2 id="part-two">Part two!</h2>' in html_body


def test_lists_tasks_and_ordered():
    out = body("- a\n- b\n\n1. one\n2. two\n\n- [ ] todo\n- [x] done\n")
    assert "<ul><li>a</li><li>b</li></ul>" in out and "<ol><li>one</li><li>two</li></ol>" in out
    assert '<input type="checkbox" disabled > todo' in out
    assert '<input type="checkbox" disabled checked > done' in out


def test_code_block_quote_rule_and_table():
    out = body("```python\nprint('<hi>')\n```\n\n> quoted *text*\n\n---\n\n"
               "| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert '<pre><code class="language-python">print(&#x27;&lt;hi&gt;&#x27;)</code></pre>' in out
    assert "<blockquote><p>quoted <em>text</em></p></blockquote>" in out and "<hr>" in out
    assert "<th>a</th><th>b</th>" in out and "<td>1</td><td>2</td>" in out


def test_paragraph_lines_are_joined():
    assert body("one\ntwo\n\nthree") == "<p>one two</p>\n<p>three</p>"


def test_cli_dry_run_apply_and_overwrite_refusal(tmp_path, capsys):
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nHello **world**.\n")
    assert m2h.main([str(source)]) == 0
    assert "Dry run" in capsys.readouterr().out and not (tmp_path / "notes.html").exists()
    assert m2h.main([str(source), "--apply"]) == 0
    page = (tmp_path / "notes.html").read_text()
    assert "<title>Notes</title>" in page and "<strong>world</strong>" in page and "<style>" in page
    assert m2h.main([str(source), "--apply"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert m2h.main([str(source), "-o", str(tmp_path / "plain.html"), "--no-style", "--apply",
                     "--title", "Custom"]) == 0
    plain = (tmp_path / "plain.html").read_text()
    assert "<style>" not in plain and "<title>Custom</title>" in plain
