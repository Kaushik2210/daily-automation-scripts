from hosts_file_viewer import find_duplicates, main, parse_hosts

SAMPLE = """# Copyright notice
# This is just a comment line

127.0.0.1   localhost
::1         localhost ip6-localhost  # loopback
192.168.1.5 nas.local nas
# 10.0.0.9 oldbox.local
10.0.0.1 nas.local
"""


def test_parse_skips_plain_comments_and_reads_fields():
    entries = parse_hosts(SAMPLE)
    assert [e["ip"] for e in entries] == ["127.0.0.1", "::1", "192.168.1.5", "10.0.0.9", "10.0.0.1"]
    assert entries[1]["names"] == ["localhost", "ip6-localhost"]
    assert entries[1]["comment"] == "loopback"
    assert [e["active"] for e in entries] == [True, True, True, False, True]


def test_find_duplicates_only_for_different_addresses():
    assert find_duplicates(parse_hosts(SAMPLE)) == ["nas.local"]
    assert find_duplicates(parse_hosts("1.1.1.1 a\n1.1.1.1 a\n")) == []


def test_cli_hides_inactive_unless_all(tmp_path, capsys):
    f = tmp_path / "hosts"
    f.write_text(SAMPLE)
    main(["--file", str(f)])
    assert "oldbox" not in capsys.readouterr().out
    main(["--file", str(f), "--all", "--search", "oldbox"])
    out = capsys.readouterr().out
    assert "oldbox.local" in out and "(off)" in out


def test_missing_file_reports_error(tmp_path, capsys):
    assert main(["--file", str(tmp_path / "nope")]) == 1
    assert "Can't read" in capsys.readouterr().err
