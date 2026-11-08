import page_text_extractor as pte

PAGE = """<html><head><title> My  Post </title><style>p{}</style></head><body>
<header><a href="/">Site banner</a></header>
<nav><a href="/">Home</a></nav>
<article>
<header><h1>Real headline</h1></header>
<p>First paragraph with <b>bold</b> and a <a href="/x">link</a>.</p>
<h2>Sub heading</h2>
<ul><li>one</li><li>two</li></ul>
<blockquote>Wise words</blockquote>
<script>var junk = 1;</script>
<aside>Related stuff</aside>
</article>
<footer>Copyright</footer></body></html>"""


def test_extracts_only_the_article_text():
    title, blocks = pte.extract(PAGE)
    assert title == "My Post"
    assert [(b["kind"], b["text"]) for b in blocks] == [
        ("h1", "Real headline"),
        ("p", "First paragraph with bold and a link."),
        ("h2", "Sub heading"), ("li", "one"), ("li", "two"), ("blockquote", "Wise words")]


def test_falls_back_to_main_and_then_whole_page():
    _, blocks = pte.extract("<nav>Menu</nav><main><p>Main text</p></main><p>Other</p>")
    assert [b["text"] for b in blocks] == ["Main text"]
    title, blocks = pte.extract("<h1>Plain</h1><p>Body text</p><footer>skip</footer>")
    assert title == "Plain" and [b["text"] for b in blocks] == ["Plain", "Body text"]


def test_site_header_is_dropped_when_there_is_no_article():
    _, blocks = pte.extract("<header>Logo</header><p>Hello there</p>")
    assert [b["text"] for b in blocks] == ["Hello there"]


def test_render_markdown_style_and_wrapping():
    blocks = [{"kind": "h2", "text": "Title"}, {"kind": "li", "text": "item " * 10},
              {"kind": "blockquote", "text": "quoted"}, {"kind": "p", "text": "word " * 30}]
    text = pte.render(blocks, 30)
    assert text.startswith("## Title\n\n- item item")
    assert "\n  item" in text and "> quoted" in text
    assert max(len(line) for line in text.splitlines()) <= 30


def test_cli_prints_summary_and_saves_without_overwriting(tmp_path, capsys):
    page, out = tmp_path / "post.html", tmp_path / "post.txt"
    page.write_text(PAGE)
    assert pte.main([str(page)]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("My Post\n(") and "min read)" in printed
    assert "# Real headline" in printed
    assert "Site banner" not in printed and "Copyright" not in printed
    assert pte.main([str(page), "--out", str(out)]) == 0
    assert out.read_text().startswith("# My Post\n\n# Real headline")
    out.write_text("keep")
    assert pte.main([str(page), "--out", str(out)]) == 1
    assert out.read_text() == "keep"


def test_empty_page_and_missing_file(tmp_path, capsys):
    page = tmp_path / "e.html"
    page.write_text("<script>x</script>")
    assert pte.main([str(page)]) == 1
    assert pte.main([str(tmp_path / "gone.html")]) == 1
