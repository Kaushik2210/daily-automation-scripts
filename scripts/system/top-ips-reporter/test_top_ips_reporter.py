import pytest
import top_ips_reporter as tir


def line(ip, status=200, size=100, path="/", stamp="10/Nov/2026:09:00:00"):
    return f'{ip} - - [{stamp} +0000] "GET {path} HTTP/1.1" {status} {size} "-" "agent"'


LOG = "\n".join([
    line("203.0.113.7", 200, 1000, "/a", "10/Nov/2026:09:00:00"),
    line("203.0.113.7", 200, 2000, "/a", "10/Nov/2026:09:05:00"),
    line("203.0.113.7", 404, 0, "/b", "10/Nov/2026:09:10:00"),
    line("203.0.113.99", 200, 500, "/", "10/Nov/2026:09:01:00"),
    line("198.51.100.5", 500, 10, "/api", "10/Nov/2026:09:02:00"),
    "garbage line", ""])


def rows():
    return [tir.parse_line(x) for x in LOG.splitlines() if tir.parse_line(x)]


def test_parse_line_and_bad_input():
    row = tir.parse_line(line("1.2.3.4", 301, 55, "/x?y=1"))
    assert (row["ip"], row["status"], row["bytes"], row["path"]) == ("1.2.3.4", 301, 55, "/x?y=1")
    assert tir.parse_line('1.2.3.4 - - [10/Nov/2026:09:00:00 +0000] "GET / HTTP/1.1" 200 -')[
        "bytes"] == 0
    assert tir.parse_line("not a log line") is None
    assert tir.parse_line('1.2.3.4 - - [99/Nov/2026:99:00:00 +0000] "GET / HTTP/1.1" 200 1') is None


def test_group_key_networks():
    assert tir.group_key("203.0.113.77", 24) == "203.0.113.0/24"
    assert tir.group_key("203.0.113.77", None) == "203.0.113.77"
    assert tir.group_key("2001:db8::1", 32) == "2001:db8::/32"
    assert tir.group_key("not-an-ip", 24) == "not-an-ip"


def test_tally_counts_bytes_errors_and_time_range():
    stats = tir.tally(rows())
    top = stats["203.0.113.7"]
    assert (top["requests"], top["bytes"], top["errors"]) == (3, 3000, 1)
    assert top["first"].minute == 0 and top["last"].minute == 10
    assert dict(top["paths"]) == {"/a": 2, "/b": 1}


def test_network_grouping_and_exclusions():
    grouped = tir.tally(rows(), prefix=24)
    assert grouped["203.0.113.0/24"]["requests"] == 4 and len(grouped) == 2
    assert "203.0.113.7" not in tir.tally(rows(), skip={"203.0.113.7"})


def test_ranked_by_each_measure():
    stats = tir.tally(rows())
    assert [n for n, _ in tir.ranked(stats)] == ["203.0.113.7", "198.51.100.5", "203.0.113.99"]
    assert [n for n, _ in tir.ranked(stats, "bytes")][0] == "203.0.113.7"
    assert [n for n, _ in tir.ranked(stats, "errors")] == [  # ties are broken by address
        "198.51.100.5", "203.0.113.7", "203.0.113.99"]


def test_report(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    assert tir.main([str(path), "--top", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("5 request(s) from 3 IP(s); 1 unreadable line(s) skipped. "
                          "Ranked by requests.")
    assert "203.0.113.7" in out and "60.0%" in out and "2.9 KB" in out
    assert "most requested: /a" in out and "... and 1 more." in out


def test_noisy_ips_are_flagged(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text("\n".join(line("9.9.9.9", 404) for _ in range(6)) + "\n" +
                    "\n".join(line("8.8.8.8", 200) for _ in range(6)) + "\n")
    assert tir.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert out.count("<-- mostly errors") == 1 and out.index("9.9.9.9") < out.index("<-- mostly")


def test_network_option_and_exclude(tmp_path, capsys):
    path = tmp_path / "access.log"
    path.write_text(LOG)
    assert tir.main([str(path), "--network", "24", "--exclude-ip", "198.51.100.5"]) == 0
    out = capsys.readouterr().out
    assert "1 network(s)" in out and "203.0.113.0/24" in out


def test_errors_and_empty_logs(tmp_path, capsys):
    empty = tmp_path / "empty.log"
    empty.write_text("nothing useful\n")
    assert tir.main([str(empty)]) == 1
    assert "No access-log requests found." in capsys.readouterr().out
    assert tir.main([str(tmp_path / "gone.log")]) == 1
    for args in (["--top", "0"], ["--network", "0"], ["--network", "200"]):
        with pytest.raises(SystemExit):
            tir.main([str(empty), *args])
