import json
import shutil

import pytest
import screenshot_indexer as si
from PIL import Image


def shot(folder, name, text=None, size=(40, 30)):
    path = folder / name
    Image.new("RGB", size, "white").save(path)
    if text is not None:
        (folder / f"{name}.txt").write_text(text)
    return path


@pytest.fixture(autouse=True)
def no_tesseract(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)


def test_ocr_text_prefers_sidecar_files(tmp_path):
    shot(tmp_path, "a.png", "Error 403 denied")
    shot(tmp_path, "b.png")
    (tmp_path / "b.txt").write_text("alternate sidecar")
    shot(tmp_path, "c.png")
    assert si.ocr_text(tmp_path / "a.png") == ("Error 403 denied", "sidecar")
    assert si.ocr_text(tmp_path / "b.png") == ("alternate sidecar", "sidecar")
    assert si.ocr_text(tmp_path / "c.png") == ("", "none")


def test_describe_reads_size_text_and_date_and_reuses_unchanged(tmp_path):
    path = shot(tmp_path, "Screenshot 2026-11-20 at 10.15.png", "Total due 1,250 USD", (50, 20))
    entry, changed = si.describe(path)
    assert changed and (entry["width"], entry["height"]) == (50, 20)
    assert entry["text"] == "Total due 1,250 USD" and entry["date"] == "2026-11-20"
    again, changed_again = si.describe(path, entry)
    assert again == entry and not changed_again


def test_snippet_centres_on_the_match():
    text = "x" * 50 + " the invoice total is here " + "y" * 50
    result = si.snippet(text, ["invoice"])
    assert "invoice" in result and result.startswith("...") and result.endswith("...")
    assert si.snippet("short text", ["zzz"]) == "short text"


def test_search_requires_all_words_and_matches_names():
    index = {"images": {"login.png": {"text": "Sign in again to continue"},
                        "invoice.png": {"text": "Total due 1250 USD"}}}
    assert [n for n, _ in si.search(index, "sign continue")[0]] == ["login.png"]
    assert [n for n, _ in si.search(index, "invoice")[0]] == ["invoice.png"]
    assert si.search(index, "sign invoice")[0] == []


def test_index_dry_run_apply_and_incremental(tmp_path, capsys):
    folder = tmp_path / "shots"
    folder.mkdir()
    shot(folder, "a.png", "Error 403 access denied")
    shot(folder, "b.png", "Meeting agenda flask upgrade")
    (folder / "bad.png").write_text("not an image")
    index = tmp_path / "idx.json"
    assert si.main(["index", str(folder), "--index", str(index)]) == 0
    out = capsys.readouterr().out
    assert "skip bad.png" in out and "2 new, 0 updated, 0 unchanged" in out
    assert "Dry run" in out and not index.exists()
    assert si.main(["index", str(folder), "--index", str(index), "--apply"]) == 0
    assert set(json.loads(index.read_text())["images"]) == {"a.png", "b.png"}
    capsys.readouterr()
    shot(folder, "c.png", "Invoice 4821")
    assert si.main(["index", str(folder), "--index", str(index), "--apply"]) == 0
    assert "1 new, 0 updated, 2 unchanged" in capsys.readouterr().out


def test_search_cli(tmp_path, capsys):
    folder = tmp_path / "s"
    folder.mkdir()
    shot(folder, "login.png", "Error 403: Access denied. Please sign in again to continue.")
    index = tmp_path / "idx.json"
    si.main(["index", str(folder), "--index", str(index), "--apply"])
    capsys.readouterr()
    assert si.main(["search", "ACCESS denied", "--index", str(index)]) == 0
    out = capsys.readouterr().out
    assert "login.png  (40x30)" in out and "1 match(es) in 1 indexed" in out
    assert si.main(["search", "zebra", "--index", str(index)]) == 1
    assert si.main(["search", "x", "--index", str(tmp_path / "none.json")]) == 1
    assert "No index" in capsys.readouterr().err


def test_warns_when_no_text_source_exists(tmp_path, capsys):
    folder = tmp_path / "s"
    folder.mkdir()
    shot(folder, "a.png")
    assert si.main(["index", str(folder), "--index", str(tmp_path / "i.json")]) == 0
    assert "No text was found" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        si.main(["index", str(tmp_path / "missing")])
