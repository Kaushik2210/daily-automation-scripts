import os
import sys
import time
from pathlib import Path

import folder_watcher as fw
import pytest


def touch(path, text="x", age=100):
    path.write_text(text)
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


def test_scan_filters_patterns_and_temp_files(tmp_path):
    touch(tmp_path / "a.csv")
    touch(tmp_path / "b.txt")
    touch(tmp_path / "c.tmp")
    touch(tmp_path / ".hidden")
    (tmp_path / "sub").mkdir()
    touch(tmp_path / "sub" / "d.csv")
    assert sorted(p.name for p in fw.scan(tmp_path, "*", False)) == ["a.csv", "b.txt"]
    assert sorted(p.name for p in fw.scan(tmp_path, "*.csv", True)) == ["a.csv", "d.csv"]


def test_changes_new_vs_changed():
    before = {Path("a"): (1, 10), Path("b"): (1, 10)}
    after = {Path("a"): (1, 10), Path("b"): (2, 20), Path("c"): (1, 5)}
    assert fw.changes(before, after, "new") == [(Path("c"), "new")]
    assert fw.changes(before, after, "changed") == [(Path("b"), "changed")]
    assert fw.changes(before, after, "both") == [(Path("b"), "changed"), (Path("c"), "new")]


def test_build_command_substitutes_after_splitting():
    path = Path("/data/My Reports/q3 summary.csv")
    command = fw.build_command("python convert.py {path} --name {stem} --ext {ext}", path)
    assert command[:2] == ["python", "convert.py"] and command[2] == str(path)
    assert command[-4:] == ["--name", "q3 summary", "--ext", "csv"]
    with pytest.raises(KeyError):
        fw.build_command("echo {nope}", path)


def test_handle_dry_run_and_real_run(tmp_path):
    lines = []
    target = touch(tmp_path / "a.txt")
    template = f"{sys.executable} -c \"import sys; sys.exit(3)\" {{name}}"
    assert fw.handle(target, "new", template, False, lines.append) is None
    assert lines[0].startswith("new     a.txt") and "would run:" in lines[1]
    assert fw.handle(target, "new", template, True, lines.append) == 3
    assert lines[-1] == "  exit code 3"
    assert fw.handle(target, "new", "echo {bad}", True, lines.append) == 1
    assert fw.handle(target, "new", None, False, lines.append) is None


def test_missing_program_is_reported(tmp_path):
    lines = []
    target = touch(tmp_path / "a.txt")
    assert fw.handle(target, "new", "definitely-not-a-program-xyz {path}", True, lines.append) == 1
    assert "failed to run" in lines[-1]


def test_watch_once_with_existing_files_and_settle(tmp_path):
    touch(tmp_path / "old.csv")
    touch(tmp_path / "fresh.csv", age=0)  # still being written
    lines = []
    count = fw.watch(tmp_path, "*.csv", False, "new", None, False, 1, 0, True, 5,
                     sleep=lambda s: None, out=lines.append)
    assert count == 1 and lines == ["new     old.csv"]


def test_watch_notices_files_that_appear_later(tmp_path):
    touch(tmp_path / "existing.txt")
    lines, ticks = [], [0]

    def fake_sleep(seconds):
        ticks[0] += 1
        if ticks[0] == 1:
            touch(tmp_path / "arrived.txt")
        if ticks[0] == 2:
            touch(tmp_path / "existing.txt", "changed!", age=0.0)

    clock_values = iter(range(0, 100, 1))
    count = fw.watch(tmp_path, "*", False, "new", None, False, 1, 3, False, 0,
                     sleep=fake_sleep, clock=lambda: next(clock_values) + time.time(),
                     out=lines.append)
    assert lines == ["new     arrived.txt"] and count == 1


def test_cli_once_dry_run_and_apply(tmp_path, capsys):
    touch(tmp_path / "a.csv")
    touch(tmp_path / "b.txt")
    template = f"{sys.executable} -c \"print(1)\" {{name}}"
    assert fw.main([str(tmp_path), "--once", "--pattern", "*.csv", "--run", template]) == 0
    out = capsys.readouterr().out
    assert "new     a.csv" in out and "would run:" in out and "b.txt" not in out
    assert "Use --apply to run the command." in out
    assert fw.main([str(tmp_path), "--once", "--run", template, "--apply"]) == 0
    assert "exit code 0" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        fw.main([str(tmp_path / "nope")])
    with pytest.raises(SystemExit):
        fw.main([str(tmp_path), "--interval", "0"])
