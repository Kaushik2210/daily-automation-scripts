import json
import textwrap

from build_site import browser_support, build, plan_info

SCRIPT = textwrap.dedent('''
    """Shout a word."""
    import argparse


    def main(argv=None):
        parser = argparse.ArgumentParser()
        parser.add_argument("word")
        print(parser.parse_args(argv).word.upper())
''')


def make_root(tmp_path):
    folder = tmp_path / "scripts" / "text" / "shout-it"
    folder.mkdir(parents=True)
    (folder / "shout_it.py").write_text(SCRIPT)
    (tmp_path / "PLAN.md").write_text(
        "## Day 03 - Demo\n- [ ] 07. shout-it - Shout a word (text)\n")
    return tmp_path


def test_browser_support_rules():
    assert browser_support("import os\nimport json")["ok"]
    assert not browser_support("import urllib.request")["ok"]
    assert not browser_support("from urllib import request")["ok"]
    assert not browser_support("import subprocess")["ok"]
    assert browser_support("from urllib.parse import quote")["ok"]
    pil = browser_support("from PIL import Image")
    assert pil["ok"] and pil["packages"] == ["pillow"]
    assert "requests" in browser_support("import requests")["reason"]


def test_plan_info(tmp_path):
    assert plan_info(make_root(tmp_path)) == {"shout-it": ("03", "07")}


def test_build_writes_pages_and_data(tmp_path):
    root = make_root(tmp_path / "repo")
    out = tmp_path / "site"
    tools = build(out, root, repo="https://example.test/repo")
    assert [t["id"] for t in tools] == ["text/shout-it"]
    page = (out / "tools" / "text" / "shout-it" / "index.html").read_text()
    assert 'content="../../../"' in page and 'content="text/shout-it"' in page
    data = json.loads((out / "data" / "tools.json").read_text())
    tool = data["tools"][0]
    assert tool["day"] == "03" and tool["browser"]["ok"]
    assert tool["schema"]["arguments"][0]["dest"] == "word"
    assert (out / tool["source"]).read_text() == SCRIPT
    assert (out / "static" / "app.js").exists() and (out / ".nojekyll").exists()
