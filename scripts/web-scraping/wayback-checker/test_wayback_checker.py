import argparse
import json

import pytest
import wayback_checker as wc

FOUND = {"url": "example.com", "archived_snapshots": {"closest": {
    "status": "200", "available": True, "timestamp": "20240115083000",
    "url": "http://web.archive.org/web/20240115083000/http://example.com/"}}}
NONE = {"url": "gone.test", "archived_snapshots": {}}


def test_parse_snapshot_found_missing_and_malformed():
    when, link = wc.parse_snapshot(FOUND)
    assert (when.year, when.month, when.day, when.hour, when.minute) == (2024, 1, 15, 8, 30)
    assert link == "https://web.archive.org/web/20240115083000/http://example.com/"
    assert wc.parse_snapshot(NONE) is None
    assert wc.parse_snapshot({}) is None
    bad = {"archived_snapshots": {"closest": {"available": True, "url": "x", "timestamp": "soon"}}}
    assert wc.parse_snapshot(bad) is None


def test_describe():
    assert wc.describe("a.test", None) == "a.test: no snapshot saved"
    assert wc.describe("example.com", wc.parse_snapshot(FOUND)).startswith(
        "example.com: 2024-01-15 08:30 UTC  https://web.archive.org/web/2024")


def test_check_timestamp():
    assert wc.check_timestamp("2020") == "2020"
    for bad in ("20", "2020-01-01", "abcd"):
        with pytest.raises(argparse.ArgumentTypeError, match="use YYYY"):
            wc.check_timestamp(bad)


def test_read_urls_skips_comments_and_blanks(tmp_path):
    f = tmp_path / "urls.txt"
    f.write_text("# my pages\nhttps://a.test\n\n  b.test  \n")
    assert wc.read_urls(f) == ["https://a.test", "b.test"]


def test_saved_response_mode(tmp_path, capsys):
    f = tmp_path / "wb.json"
    f.write_text(json.dumps([FOUND, NONE]))
    assert wc.main(["--response", str(f)]) == 1
    out = capsys.readouterr().out
    assert "example.com: 2024-01-15 08:30 UTC" in out and "gone.test: no snapshot" in out
    assert "1 of 2 URL(s) have a snapshot." in out
    f.write_text(json.dumps(FOUND))
    assert wc.main(["--response", str(f)]) == 0


def test_lookup_mode_uses_the_api_helper(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_lookup(url, timestamp=None):
        calls.append((url, timestamp))
        return FOUND if "example" in url else NONE

    monkeypatch.setattr(wc, "lookup", fake_lookup)
    listing = tmp_path / "u.txt"
    listing.write_text("gone.test\n")
    assert wc.main(["example.com", "--file", str(listing), "--timestamp", "2024", "--delay",
                    "0"]) == 1
    assert calls == [("example.com", "2024"), ("gone.test", "2024")]
    assert "1 of 2" in capsys.readouterr().out


def test_bad_input(tmp_path, capsys):
    with pytest.raises(SystemExit):
        wc.main([])
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert wc.main(["--response", str(broken)]) == 1
    assert "Couldn't complete" in capsys.readouterr().err
