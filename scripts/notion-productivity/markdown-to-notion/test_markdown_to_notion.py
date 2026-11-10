import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import markdown_to_notion as m2n
import pytest


def texts(parts):
    return [(p["text"]["content"], sorted(p.get("annotations", {})),
             (p["text"].get("link") or {}).get("url")) for p in parts]


def test_inline_formatting():
    parts = m2n.inline("Plain **bold** and *italic* with `code`, ~~gone~~ and [a link](https://x.test).")
    assert texts(parts) == [
        ("Plain ", [], None), ("bold", ["bold"], None), (" and ", [], None),
        ("italic", ["italic"], None), (" with ", [], None), ("code", ["code"], None),
        (", ", [], None), ("gone", ["strikethrough"], None), (" and ", [], None),
        ("a link", [], "https://x.test"), (".", [], None)]
    assert texts(m2n.inline("snake_case_name and _real italic_")) == [
        ("snake_case_name and ", [], None), ("real italic", ["italic"], None)]


def test_long_text_is_split_below_notions_limit():
    parts = m2n.inline("x" * 4500)
    assert [len(p["text"]["content"]) for p in parts] == [2000, 2000, 500]


def kinds(blocks):
    return [b["type"] for b in blocks]


SAMPLE = """# Title

Intro line one
continues here.

## Section
- one
  - nested **bold**
- [ ] todo
- [x] done
1. first
2. second
> quoted
---
```py
x = **not bold**
```
![alt text](https://x.test/pic.png)
### Deep
#### Deeper
"""


def test_convert_structure():
    blocks = m2n.convert(SAMPLE)
    assert kinds(blocks) == ["heading_1", "paragraph", "heading_2", "bulleted_list_item", "to_do",
                             "to_do", "numbered_list_item", "numbered_list_item", "quote",
                             "divider", "code", "image", "heading_3", "heading_3"]
    intro = blocks[1]["paragraph"]["rich_text"][0]["text"]["content"]
    assert intro == "Intro line one continues here."
    nested = blocks[3]["bulleted_list_item"]["children"]
    assert kinds(nested) == ["bulleted_list_item"]
    assert nested[0]["bulleted_list_item"]["rich_text"][1]["annotations"] == {"bold": True}
    assert [b["to_do"]["checked"] for b in blocks[4:6]] == [False, True]
    code = blocks[10]["code"]
    assert code["language"] == "python"
    assert code["rich_text"][0]["text"]["content"] == "x = **not bold**"
    assert "annotations" not in code["rich_text"][0]  # no markdown inside code
    assert blocks[11]["image"]["external"]["url"] == "https://x.test/pic.png"
    assert blocks[11]["image"]["caption"][0]["text"]["content"] == "alt text"


def test_unknown_languages_fall_back_and_count_includes_children():
    blocks = m2n.convert("```klingon\nqapla\n```\n\n- a\n  - b\n    - c\n")
    assert blocks[0]["code"]["language"] == "plain text"
    assert m2n.count_blocks(blocks) == 4


def test_cli_dry_run_summary_and_json(tmp_path, capsys):
    f = tmp_path / "n.md"
    f.write_text(SAMPLE)
    assert m2n.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("n.md: 14 top-level block(s), 15 in all") and "Dry run" in out
    assert m2n.main([str(f), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["type"] == "heading_1"
    f.write_text("\n\n")
    assert m2n.main([str(f)]) == 1
    with pytest.raises(SystemExit):
        m2n.main([str(f), "--apply"])
    with pytest.raises(SystemExit):
        m2n.main([str(tmp_path / "gone.md")])


class Fake(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args):
        pass

    def do_PATCH(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.calls.append((self.path, self.headers.get("Authorization"), len(body["children"])))
        code = 404 if "/missing/" in self.path else 200
        self.send_response(code)
        self.end_headers()
        self.wfile.write(b"{}")


@pytest.fixture
def server(monkeypatch):
    Fake.calls = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(m2n, "API", f"http://127.0.0.1:{httpd.server_address[1]}")
    monkeypatch.setenv("NOTION_TOKEN", "secret_x")
    yield httpd
    httpd.shutdown()


def test_apply_sends_batches_of_100_to_the_right_page(server, tmp_path, capsys):
    f = tmp_path / "big.md"
    f.write_text("\n\n".join(f"Paragraph {i}" for i in range(230)))
    page = "https://www.notion.so/My-Page-0123456789abcdef0123456789abcdef"
    assert m2n.main([str(f), "--page", page, "--apply", "--delay", "0"]) == 0
    assert [c[2] for c in Fake.calls] == [100, 100, 30]
    assert all(c[0] == "/blocks/0123456789abcdef0123456789abcdef/children" for c in Fake.calls)
    assert Fake.calls[0][1] == "Bearer secret_x"
    assert "Appended 230 block(s)" in capsys.readouterr().out


def test_apply_errors(server, monkeypatch, tmp_path, capsys):
    f = tmp_path / "n.md"
    f.write_text("hi")
    assert m2n.main([str(f), "--page", "missing", "--apply", "--delay", "0"]) == 1
    assert Fake.calls == [("/blocks/missing/children", "Bearer secret_x", 1)]
    assert "404 (page not found" in capsys.readouterr().err
    monkeypatch.delenv("NOTION_TOKEN")
    assert m2n.main([str(f), "--page", "p1", "--apply"]) == 1
    assert "NOTION_TOKEN" in capsys.readouterr().err
