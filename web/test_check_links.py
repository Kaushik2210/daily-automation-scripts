import json

import check_links


def fake_fetch(pages):
    def fetch(url, timeout=20):
        if url in pages:
            return 200, pages[url]
        return 404, ""
    return fetch


def test_all_links_ok(monkeypatch):
    tools = json.dumps({"tools": [{"id": "text/a", "source": "src/text/a/a.py"}]})
    monkeypatch.setattr(check_links, "fetch", fake_fetch({
        "https://x.test/data/tools.json": tools,
        "https://x.test/tools/text/a/": '<meta name="app-tool" content="text/a">',
        "https://x.test/src/text/a/a.py": "print('hi')",
    }))
    assert check_links.check_site("https://x.test") == []


def test_reports_missing_page_and_source(monkeypatch):
    tools = json.dumps({"tools": [{"id": "text/a", "source": "src/text/a/a.py"}]})
    monkeypatch.setattr(check_links, "fetch", fake_fetch({"https://x.test/data/tools.json": tools}))
    problems = check_links.check_site("https://x.test/")
    assert len(problems) == 2
    assert "tools/text/a/" in problems[0]


def test_unreachable_site(monkeypatch):
    monkeypatch.setattr(check_links, "fetch", fake_fetch({}))
    assert check_links.check_site("https://x.test")[0].endswith("-> 404")
