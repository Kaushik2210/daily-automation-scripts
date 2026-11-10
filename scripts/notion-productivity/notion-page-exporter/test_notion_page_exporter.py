import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import notion_page_exporter as npe
import pytest


def t(s, href=None, **ann):
    return {"plain_text": s, "href": href, "annotations": ann}


def blk(kind, parts=(), block_id="b", has_children=False, **extra):
    return {"id": block_id, "type": kind, "has_children": has_children,
            kind: {"rich_text": list(parts), **extra}}


def test_rich_applies_annotations_links_and_keeps_spacing():
    assert npe.rich([t("Hello "), t("world", bold=True), t("!")]) == "Hello **world**!"
    assert npe.rich([t(" padded ", italic=True)]) == " *padded* "
    assert npe.rich([t("x", code=True, bold=True)]) == "**`x`**"
    assert npe.rich([t("doc", "https://x.test", strikethrough=True)]) == "[~~doc~~](https://x.test)"
    assert npe.rich(None) == "" and npe.rich([t("   ")]) == "   "


def test_headings_lists_todos_quotes_code_and_dividers():
    blocks = [blk("heading_2", [t("Goals")]), blk("bulleted_list_item", [t("one")]),
              blk("numbered_list_item", [t("first")]), blk("numbered_list_item", [t("second")]),
              blk("paragraph", [t("Break")]), blk("numbered_list_item", [t("restart")]),
              blk("to_do", [t("done")], checked=True), blk("to_do", [t("open")], checked=False),
              blk("quote", [t("wise")]), blk("code", [t("x = 1")], language="python"),
              blk("code", [t("plain")], language="plain text"),
              {"id": "d", "type": "divider", "divider": {}},
              blk("callout", [t("careful")], icon={"emoji": "!"}),
              {"id": "u", "type": "synced_block", "synced_block": {}}]
    md = "\n".join(npe.blocks_to_markdown(blocks))
    assert "## Goals" in md and "- one" in md
    assert "1. first\n2. second" in md and "1. restart" in md
    assert "- [x] done\n- [ ] open" in md and "> wise" in md
    assert "```python\nx = 1\n```" in md and "```\nplain\n```" in md
    assert "---" in md and "> ! careful" in md
    assert "<!-- unsupported block: synced_block -->" in md


def test_nested_children_are_indented_and_tables_converted():
    kids = {"list": [blk("bulleted_list_item", [t("child")], "c1")],
            "tbl": [{"table_row": {"cells": [[t("A")], [t("B")]]}},
                    {"table_row": {"cells": [[t("1")], [t("2")]]}}]}
    blocks = [blk("bulleted_list_item", [t("parent")], "list", True),
              {"id": "tbl", "type": "table", "has_children": True, "table": {}}]
    md = "\n".join(npe.blocks_to_markdown(blocks, lambda block_id: kids[block_id]))
    assert "- parent\n  - child" in md
    assert "| A | B |\n| --- | --- |\n| 1 | 2 |" in md


def test_to_markdown_and_slugify():
    md = npe.to_markdown("My Page", [blk("paragraph", [t("a")]), blk("paragraph", []),
                                      blk("paragraph", [t("b")])])
    assert md == "# My Page\n\na\n\nb\n"
    assert npe.slugify("Q4 Plan: Final!") == "q4-plan-final" and npe.slugify("???") == "page"


def test_from_file_prints_and_respects_dry_run(tmp_path, capsys):
    src, out = tmp_path / "blocks.json", tmp_path / "md"
    blocks = [blk("heading_1", [t("Hi")]), blk("paragraph", [t("x")])]
    src.write_text(json.dumps({"results": blocks}))
    assert npe.main(["--from-file", str(src), "--title", "My Notes"]) == 0
    assert capsys.readouterr().out == "# My Notes\n\n# Hi\n\nx\n"
    assert npe.main(["--from-file", str(src), "--title", "My Notes", "--out-dir", str(out)]) == 0
    assert "would write" in capsys.readouterr().out and not out.exists()
    assert npe.main(["--from-file", str(src), "--title", "My Notes", "--out-dir", str(out),
                     "--apply"]) == 0
    assert (out / "my-notes.md").read_text().startswith("# My Notes")
    (out / "my-notes.md").write_text("keep")
    assert npe.main(["--from-file", str(src), "--title", "My Notes", "--out-dir", str(out),
                     "--apply"]) == 0
    assert (out / "my-notes.md").read_text() == "keep"


def test_argument_and_file_errors(tmp_path, capsys):
    with pytest.raises(SystemExit):
        npe.main([])
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    assert npe.main(["--from-file", str(bad)]) == 1


PAGE_ID = "0123456789abcdef0123456789abcdef"


class Fake(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        Fake.seen.append((self.path, self.headers.get("Authorization")))
        path = self.path.split("?")[0]
        if path == f"/pages/{PAGE_ID}":
            body = {"properties": {"Name": {"type": "title", "title": [t("Live Page")]}}}
        elif path == f"/blocks/{PAGE_ID}/children":
            first = "start_cursor" not in self.path
            body = {"results": [blk("heading_1", [t("One")], "h", False)] if first else
                    [blk("bulleted_list_item", [t("parent")], "kid", True)],
                    "has_more": first, "next_cursor": "c2" if first else None}
        elif path == "/blocks/kid/children":
            body = {"results": [blk("bulleted_list_item", [t("nested")], "n")], "has_more": False}
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


@pytest.fixture
def server(monkeypatch):
    Fake.seen = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(npe, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("NOTION_TOKEN", "secret_x")
    yield httpd
    httpd.shutdown()


def test_live_export_pages_through_blocks_and_children(server, capsys):
    url = f"https://www.notion.so/Live-Page-{PAGE_ID}?pvs=4"
    assert npe.main([url]) == 0
    out = capsys.readouterr().out
    assert out == "# Live Page\n\n# One\n\n- parent\n  - nested\n"
    assert all(auth == "Bearer secret_x" for _, auth in Fake.seen)


def test_live_errors(server, monkeypatch, capsys):
    assert npe.main(["f" * 32]) == 1
    assert "404" in capsys.readouterr().err
    monkeypatch.delenv("NOTION_TOKEN")
    assert npe.main([PAGE_ID]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err
