import meta_tag_auditor as mta

GOOD = """<!doctype html><html lang="en"><head>
<title>A perfectly sized page title for the tests</title>
<meta name="description"
 content="A description that is long enough to be useful to search engines and readers alike.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://x.test/">
<meta property="og:title" content="T"><meta property="og:description" content="D">
<meta property="og:image" content="https://x.test/i.png">
<meta property="og:url" content="https://x.test/">
<meta name="twitter:card" content="summary">
</head><body><h1>Hello</h1></body></html>"""


def status_of(results, label):
    return next(status for status, message in results if message.startswith(label))


def test_a_complete_page_passes_everything():
    results = mta.audit(GOOD)
    assert all(status == "ok" for status, _ in results), results


def test_missing_and_badly_sized_tags():
    page = "<title>Hi</title><h1>a</h1><h1>b</h1><meta name='robots' content='NoIndex'>"
    results = mta.audit(page)
    assert status_of(results, "title") == "WARN"
    assert status_of(results, "meta description") == "FAIL"
    assert status_of(results, "canonical link") == "WARN"
    assert status_of(results, "h1") == "WARN"
    assert status_of(results, "robots") == "WARN"
    assert status_of(results, "og:image") == "WARN"


def test_length_check_boundaries():
    assert mta.length_check("t", "x" * 30, 30, 60)[0] == "ok"
    assert mta.length_check("t", "x" * 61, 30, 60)[0] == "WARN"
    assert mta.length_check("t", "", 30, 60) == ("FAIL", "t: missing")


def test_whitespace_in_the_title_is_tidied_and_first_meta_wins():
    results = mta.audit("<title>\n  A   title\n of words that is long enough ok </title>")
    assert results[0] == ("ok", "title: 39 characters")
    two = "<meta name='description' content='first'><meta name='description' content='second'>"
    assert "5 characters" in mta.audit(two)[1][1]


def test_cli_exit_codes(tmp_path, capsys):
    good, bad = tmp_path / "good.html", tmp_path / "bad.html"
    good.write_text(GOOD)
    bad.write_text("<title>Home</title>")
    assert mta.main([str(good)]) == 0
    assert "11/11 checks passed" in capsys.readouterr().out
    assert mta.main([str(bad), "--problems-only"]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] meta description: missing" in out and "[ok" not in out


def test_strict_makes_warnings_fail(tmp_path):
    page = tmp_path / "p.html"
    page.write_text(GOOD.replace("<h1>Hello</h1>", ""))
    assert mta.main([str(page)]) == 0
    assert mta.main([str(page), "--strict"]) == 1
    assert mta.main([str(tmp_path / "missing.html")]) == 1
