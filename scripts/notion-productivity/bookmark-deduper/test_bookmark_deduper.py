import bookmark_deduper as bd
import pytest

EXPORT = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><H3>Dev</H3>
    <DL><p>
        <DT><A HREF="https://docs.python.org/3/" ADD_DATE="1">Python docs</A>
        <DD>The official docs
        <DT><A HREF="https://news.ycombinator.com/?utm_source=feed&amp;id=1">HN</A>
    </DL><p>
    <DT><A HREF="https://DOCS.python.org/3">Python again</A>
    <DD>duplicate description
    <DT><A HREF="https://www.news.ycombinator.com/?id=1&fbclid=x">HN again</A>
    <DT><A HREF="http://example.com/a#top">Example</A>
    <DT><A HREF="https://example.com/a/">Example slash</A>
    <DT><A HREF="https://example.com/a?page=2">Different query</A>
    <DT><A HREF="mailto:me@example.com">Mail</A>
    <DT><A HREF="mailto:me@example.com">Mail again</A>
</DL><p>
"""


@pytest.mark.parametrize("a,b", [
    ("https://example.com/a/", "http://EXAMPLE.com/a#frag"),
    ("https://www.example.com", "https://example.com/"),
    ("https://example.com:443/x", "https://example.com/x"),
    ("https://example.com/?a=1&utm_medium=m", "https://example.com/?a=1"),
    ("https://example.com/p?x=1&amp;y=2", "https://example.com/p?x=1&y=2")])
def test_same_page_different_spelling(a, b):
    assert bd.normalise(a) == bd.normalise(b)


@pytest.mark.parametrize("a,b", [
    ("https://example.com/a", "https://example.com/b"),
    ("https://example.com/?page=1", "https://example.com/?page=2"),
    ("https://example.com:8080/", "https://example.com/"),
    ("mailto:a@x.test", "mailto:b@x.test")])
def test_different_pages_stay_different(a, b):
    assert bd.normalise(a) != bd.normalise(b)


def test_find_duplicates_keeps_the_first_and_drops_descriptions():
    kept, removed, drop = bd.find_duplicates(EXPORT)
    assert [title for _, title, _ in kept] == [
        "Python docs", "HN", "Example", "Different query", "Mail"]
    assert [entry[1] for entry, _ in removed] == [
        "Python again", "HN again", "Example slash", "Mail again"]
    assert removed[0][1][1] == "Python docs"  # points back at the bookmark that was kept
    text = bd.clean_text(EXPORT, drop)
    assert "Python again" not in text and "duplicate description" not in text
    assert "The official docs" in text  # the kept bookmark's description stays
    assert text.count("<DT><A") == 5 and "<DL><p>" in text and text.endswith("</DL><p>\n")


def test_dry_run_reports_and_writes_nothing(tmp_path, capsys):
    src, out = tmp_path / "bookmarks.html", tmp_path / "clean.html"
    src.write_text(EXPORT)
    assert bd.main([str(src), "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "9 bookmark(s): 5 unique, 4 duplicate(s)." in text and "Dry run" in text
    assert "same page as line 5: Python docs" in text and not out.exists()


def test_apply_writes_a_clean_copy_and_never_touches_the_original(tmp_path, capsys):
    src, out = tmp_path / "bookmarks.html", tmp_path / "clean.html"
    src.write_text(EXPORT)
    assert bd.main([str(src), "--out", str(out), "--apply"]) == 0
    assert src.read_text() == EXPORT and "Python again" not in out.read_text()
    out.write_text("keep")
    assert bd.main([str(src), "--out", str(out), "--apply"]) == 1 and out.read_text() == "keep"


def test_no_duplicates_and_bad_input(tmp_path, capsys):
    src = tmp_path / "b.html"
    src.write_text('<DT><A HREF="https://a.test/">A</A>\n<DT><A HREF="https://b.test/">B</A>\n')
    assert bd.main([str(src)]) == 0 and "0 duplicate(s)" in capsys.readouterr().out
    src.write_text("<html>nothing here</html>")
    assert bd.main([str(src)]) == 1
    with pytest.raises(SystemExit):
        bd.main([str(src), "--apply"])
    with pytest.raises(SystemExit):
        bd.main([str(tmp_path / "gone.html")])
