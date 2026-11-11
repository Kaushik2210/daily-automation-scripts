import os

import pytest
import sync_conflict_finder as scf


def exists_in(*names):
    return set(names).__contains__


@pytest.mark.parametrize("name,kind,original", [
    ("notes (conflicted copy 2026-11-02).txt", "Dropbox/Nextcloud conflicted copy", "notes.txt"),
    ("notes (Kaushik's conflicted copy 2026-11-03).txt", "Dropbox/Nextcloud conflicted copy",
     "notes.txt"),
    ("Report (conflicted copy 2026-11-02 101500).docx", "Dropbox/Nextcloud conflicted copy",
     "Report.docx"),
    ("plan.sync-conflict-20261104-101500-ABCDEFG.md", "Syncthing conflict", "plan.md"),
    ("data.sync-conflict-20261104-101500.csv", "Syncthing conflict", "data.csv"),
    ("README (conflicted copy 2026-11-02)", "Dropbox/Nextcloud conflicted copy", "README")])
def test_classify_recognises_unambiguous_patterns(name, kind, original):
    assert scf.classify(name, exists_in()) == (kind, original)


def test_onedrive_style_needs_the_original_and_a_hostname_shape():
    assert scf.classify("budget-DESKTOP-4F2K9.xlsx", exists_in("budget.xlsx")) == (
        "OneDrive-style (computer name added)", "budget.xlsx")
    assert scf.classify("budget-DESKTOP-4F2K9.xlsx", exists_in()) is None  # no original
    assert scf.classify("summary-report.txt", exists_in("summary.txt")) is None  # not a hostname
    assert scf.classify("plan-v2.txt", exists_in("plan.txt")) is None


def test_numbered_copies_only_in_loose_mode_with_an_original():
    assert scf.classify("trip (1).jpg", exists_in("trip.jpg")) is None
    assert scf.classify("trip (1).jpg", exists_in("trip.jpg"), loose=True) == (
        "numbered copy, e.g. (1)", "trip.jpg")
    assert scf.classify("trip (1).jpg", exists_in(), loose=True) is None


def write(path, text, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mtime:
        os.utime(path, (mtime, mtime))


@pytest.fixture
def cloud(tmp_path):
    root = tmp_path / "cloud"
    write(root / "notes.txt", "latest", 1_700_000_500)
    write(root / "notes (conflicted copy 2026-11-02).txt", "latest", 1_700_000_500)
    write(root / "sub" / "plan.md", "plan v2 longer", 1_700_000_900)
    write(root / "sub" / "plan.sync-conflict-20261104-101500-ABCDEFG.md", "plan v1", 1_700_000_100)
    write(root / "orphan (conflicted copy 2026-10-01).txt", "alone")
    write(root / "photo.jpg", "jpeg")
    write(root / "photo (1).jpg", "jpeg")
    write(root / "summary-report.txt", "ordinary")
    return root


def test_find_conflicts_walks_subfolders_and_links_originals(cloud):
    found = scf.find_conflicts(cloud, [])
    rels = [c["rel"] for c in found]
    assert rels == ["notes (conflicted copy 2026-11-02).txt",
                    "orphan (conflicted copy 2026-10-01).txt",
                    "sub/plan.sync-conflict-20261104-101500-ABCDEFG.md"]
    assert found[0]["original"].name == "notes.txt" and found[1]["original"] is None
    assert "photo (1).jpg" in [c["rel"] for c in scf.find_conflicts(cloud, [], loose=True)]


def test_judge_identical_different_and_orphan(cloud):
    identical, orphan, different = scf.find_conflicts(cloud, [])
    assert scf.judge(identical)[0] == "IDENTICAL"
    assert scf.judge(orphan)[0] == "ORPHAN"
    label, why = scf.judge(different)
    assert label == "DIFFERENT" and "7 B vs 14 B" in why and "copy is older" in why


def test_cli_report_and_exit_code(cloud, capsys):
    assert scf.main([str(cloud)]) == 1
    out = capsys.readouterr().out
    assert "3 conflict copy/copies found" in out
    assert "[IDENTICAL] notes (conflicted copy 2026-11-02).txt" in out
    assert "[DIFFERENT] sub/plan.sync-conflict-20261104-101500-ABCDEFG.md" in out
    assert "[ORPHAN]" in out and "1 identical, 1 different, 1 without an original." in out
    assert "Nothing was changed or deleted." in out
    assert (cloud / "notes (conflicted copy 2026-11-02).txt").exists()


def test_excludes_loose_mode_and_clean_folders(cloud, tmp_path, capsys):
    assert scf.main([str(cloud), "--exclude", "sub", "--exclude", "orphan*"]) == 1
    assert "1 conflict copy/copies" in capsys.readouterr().out
    assert scf.main([str(cloud), "--loose"]) == 1
    assert "numbered copy" in capsys.readouterr().out
    clean = tmp_path / "clean"
    write(clean / "a.txt", "x")
    assert scf.main([str(clean)]) == 0
    assert "No sync-conflict copies found." in capsys.readouterr().out


def test_not_a_folder(tmp_path):
    with pytest.raises(SystemExit):
        scf.main([str(tmp_path / "gone")])
