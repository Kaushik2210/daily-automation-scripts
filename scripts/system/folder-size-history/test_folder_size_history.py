from datetime import datetime

from folder_size_history import folder_stats, main, read_history, record


def test_folder_stats(tmp_path):
    (tmp_path / "a.txt").write_text("12345")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("123")
    assert folder_stats(tmp_path) == (8, 2)


def test_record_writes_header_once_and_appends(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "f.txt").write_text("abc")
    log = tmp_path / "log.csv"
    record(log, folder, datetime(2026, 1, 1, 9, 0))
    (folder / "g.txt").write_text("defg")
    record(log, folder, datetime(2026, 1, 2, 9, 0))
    rows = read_history(log, folder)
    assert [r["bytes"] for r in rows] == ["3", "7"]
    assert log.read_text().count("timestamp") == 1


def test_history_filters_by_folder(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    log = tmp_path / "log.csv"
    record(log, a)
    record(log, b)
    assert len(read_history(log, a)) == 1
    assert len(read_history(log)) == 2


def test_cli_records_then_shows(tmp_path, capsys):
    folder = tmp_path / "d"
    folder.mkdir()
    (folder / "x").write_text("hello")
    log = tmp_path / "h.csv"
    main([str(folder), "--log", str(log)])
    main([str(folder), "--log", str(log), "--show"])
    out = capsys.readouterr().out
    assert "Recorded 5 B in 1 file(s)" in out
    assert out.count("1 files") >= 1
