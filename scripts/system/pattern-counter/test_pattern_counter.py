import gzip

import pattern_counter as pc
import pytest


@pytest.fixture
def logs(tmp_path):
    folder = tmp_path / "logs"
    (folder / "old").mkdir(parents=True)
    (folder / "app.log").write_text(
        "ERROR timeout talking to db1\nINFO ok\nERROR timeout talking to db2\n"
        "ERROR disk full\nWARN Timeout again, db1\n")
    with gzip.open(folder / "app.log.1.gz", "wt") as handle:
        handle.write("ERROR timeout talking to db1\nINFO ok\n")
    (folder / "old" / "ancient.log").write_text("ERROR timeout talking to db9\n")
    (folder / "notes.txt").write_text("ERROR timeout in a txt file\n")
    return folder


def test_parse_patterns_names_and_equals_signs_in_regexes():
    patterns = pc.parse_patterns(["errors=ERROR", "plain", "key=value=x", "a b=c"], 0)
    assert [label for label, _ in patterns] == ["errors", "plain", "key", "a b=c"]
    assert patterns[2][1].pattern == "value=x"
    assert pc.parse_patterns(["x" * 40], 0)[0][0] == "x" * 21 + "..."


def test_find_files_globs_recursion_and_direct_files(logs):
    def names(files):
        return [f.name for f in files]

    assert names(pc.find_files([logs], "*.log*", False)) == ["app.log", "app.log.1.gz"]
    assert names(pc.find_files([logs], "*.log*", True)) == ["app.log", "app.log.1.gz",
                                                             "ancient.log"]
    assert names(pc.find_files([logs / "notes.txt"], "*.log*", False)) == ["notes.txt"]


def test_count_file_counts_lines_and_captured_values(logs):
    patterns = pc.parse_patterns(["errors=ERROR", r"timeout=timeout talking to (\w+)"], 0)
    hits, captured, total = pc.count_file(logs / "app.log", patterns)
    assert hits == {"errors": 3, "timeout": 2} and total == 5
    assert captured["timeout"] == {"db1": 1, "db2": 1} and not captured["errors"]


def test_gz_files_are_read_transparently(logs):
    patterns = pc.parse_patterns(["ERROR"], 0)
    assert pc.count_file(logs / "app.log.1.gz", patterns)[0] == {"ERROR": 1}


def test_cli_table_totals_and_top_values(logs, capsys):
    assert pc.main([str(logs), "-p", "errors=ERROR", "-p", r"db=talking to (\w+)"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].split() == ["File", "Lines", "errors", "db"]
    assert out[1].split() == ["app.log", "5", "3", "2"]
    assert out[2].split() == ["app.log.1.gz", "2", "1", "1"]
    assert out[3].split() == ["TOTAL", "7", "4", "3"]
    assert any(line.startswith("Top values for db: db1 (2), db2 (1)") for line in out)


def test_ignore_case_recursive_and_custom_glob(logs, capsys):
    assert pc.main([str(logs), "-r", "--glob", "*.log", "-p", "TIMEOUT", "-i"]) == 0
    out = capsys.readouterr().out
    assert "ancient.log" in out and "app.log.1.gz" not in out
    assert pc.main([str(logs), "-p", "TIMEOUT"]) == 1  # case matters without -i: no matches
    capsys.readouterr()
    assert pc.main([str(logs), "-p", "TIMEOUT", "-i", "--top", "0"]) == 0


def test_broken_gz_is_reported_but_others_still_count(logs, capsys):
    (logs / "broken.log.2.gz").write_bytes(b"not really gzip")
    assert pc.main([str(logs), "-p", "ERROR"]) == 1
    captured = capsys.readouterr()
    assert "Couldn't read broken.log.2.gz" in captured.err and "app.log" in captured.out


def test_bad_arguments_and_no_files(logs, tmp_path, capsys):
    for args in (["-p", "("], ["-p", "x", "--top", "-1"]):
        with pytest.raises(SystemExit):
            pc.main([str(logs), *args])
    with pytest.raises(SystemExit):
        pc.main([str(tmp_path / "gone"), "-p", "x"])
    with pytest.raises(SystemExit):
        pc.main([str(logs)])
    empty = tmp_path / "empty"
    empty.mkdir()
    assert pc.main([str(empty), "-p", "x"]) == 1
    assert "No log files found." in capsys.readouterr().out
