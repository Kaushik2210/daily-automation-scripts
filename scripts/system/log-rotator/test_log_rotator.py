import gzip

import log_rotator as lr
import pytest


@pytest.mark.parametrize("text,size", [("500", 500), ("1KB", 1024), ("1.5mb", 1572864),
                                       ("2 G", 2 * 1024 ** 3), ("10M", 10 * 1024 ** 2)])
def test_parse_size(text, size):
    assert lr.parse_size(text) == size


@pytest.mark.parametrize("text", ["", "big", "10XB", "0", "-5"])
def test_parse_size_rejects_nonsense(text):
    with pytest.raises(Exception, match="size"):
        lr.parse_size(text)


def read_gz(path):
    return gzip.decompress(path.read_bytes()).decode()


@pytest.fixture
def logs(tmp_path):
    folder = tmp_path / "logs"
    folder.mkdir()
    (folder / "big.log").write_text("line of text\n" * 300)
    (folder / "small.log").write_text("tiny\n")
    (folder / "notes.txt").write_text("x" * 5000)
    return folder


def test_find_logs_in_folders_and_as_files(logs):
    assert [p.name for p in lr.find_logs([logs], "*.log")] == ["big.log", "small.log"]
    assert [p.name for p in lr.find_logs([logs / "notes.txt"], "*.log")] == ["notes.txt"]


def test_plan_rotation_shifts_archives_and_drops_the_oldest(logs):
    log = logs / "big.log"
    for n in (1, 2, 3):
        lr.archive_name(log, n).write_bytes(b"x")
    steps = lr.plan_rotation(log, keep=3)
    assert [(a, s.name, t.name if t else None) for a, s, t in steps] == [
        ("delete", "big.log.3.gz", None), ("rename", "big.log.2.gz", "big.log.3.gz"),
        ("rename", "big.log.1.gz", "big.log.2.gz")]
    assert lr.plan_rotation(logs / "small.log", 3) == []


def test_dry_run_changes_nothing(logs, capsys):
    before = (logs / "big.log").read_bytes()
    assert lr.main([str(logs), "--max-size", "1KB"]) == 0
    out = capsys.readouterr().out
    assert "2 log file(s), 1 at least 1.0 KB." in out and "rotate  big.log" in out
    assert "skip    small.log" in out and "Dry run" in out
    assert (logs / "big.log").read_bytes() == before and not list(logs.glob("*.gz"))


def test_apply_compresses_and_empties_the_log_in_place(logs):
    original = (logs / "big.log").read_bytes().decode()
    assert lr.main([str(logs), "--max-size", "1KB", "--apply"]) == 0
    assert read_gz(logs / "big.log.1.gz") == original
    assert (logs / "big.log").exists() and (logs / "big.log").stat().st_size == 0
    assert (logs / "small.log").read_text() == "tiny\n" and not list(logs.glob("*.new.gz"))


def test_rename_mode_removes_the_original(logs):
    original = (logs / "big.log").read_bytes().decode()
    assert lr.main([str(logs), "--max-size", "1KB", "--rename", "--apply"]) == 0
    assert not (logs / "big.log").exists() and read_gz(logs / "big.log.1.gz") == original


def test_repeated_rotation_keeps_only_n_archives(logs):
    for round_number in range(1, 6):
        (logs / "big.log").write_text(f"round {round_number}\n" * 400)
        assert lr.main([str(logs), "--max-size", "1KB", "--keep", "3", "--apply"]) == 0
    names = sorted(p.name for p in logs.glob("big.log.*.gz"))
    assert names == ["big.log.1.gz", "big.log.2.gz", "big.log.3.gz"]
    assert read_gz(logs / "big.log.1.gz").startswith("round 5")
    assert read_gz(logs / "big.log.3.gz").startswith("round 3")


def test_lines_written_after_the_snapshot_are_kept(logs, monkeypatch):
    log = logs / "big.log"
    original = log.read_bytes().decode()
    real_copy = lr.gzip.open

    def appending_open(path, mode="rb", *args, **kwargs):
        if mode == "wb":  # a program appends to the log while it is being archived
            with log.open("a") as handle:
                handle.write("written during rotation\n")
        return real_copy(path, mode, *args, **kwargs)

    monkeypatch.setattr(lr.gzip, "open", appending_open)
    lr.rotate(log, 3, rename_log=False)
    monkeypatch.undo()
    assert read_gz(logs / "big.log.1.gz") == original
    assert log.read_text() == "written during rotation\n"


def test_rename_mode_refuses_when_the_log_grew(logs, monkeypatch):
    log = logs / "big.log"
    real_open = lr.gzip.open

    def appending_open(path, mode="rb", *args, **kwargs):
        if mode == "wb":
            with log.open("a") as handle:
                handle.write("late line\n")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(lr.gzip, "open", appending_open)
    with pytest.raises(OSError, match="grew"):
        lr.rotate(log, 3, rename_log=True)
    monkeypatch.undo()
    assert log.exists() and not list(logs.glob("*.gz"))


def test_nothing_to_rotate_and_bad_arguments(logs, tmp_path, capsys):
    assert lr.main([str(logs), "--max-size", "1GB"]) == 0
    assert "Nothing needs rotating." in capsys.readouterr().out
    for args in ([str(logs)], [str(tmp_path / "gone"), "--max-size", "1KB"],
                 [str(logs), "--max-size", "1KB", "--keep", "0"]):
        with pytest.raises(SystemExit):
            lr.main(args)
