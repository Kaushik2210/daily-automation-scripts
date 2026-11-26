import csv
from datetime import datetime

import pytest
import resource_logger as rl

PROC_STAT = "cpu  100 0 50 800 50 0 0 0 0 0\ncpu0 1 2 3 4\n"
MEMINFO = "MemTotal:       16384000 kB\nMemFree:         1000000 kB\nMemAvailable:    8192000 kB\n"
VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                               10000.
Pages active:                            100000.
Pages wired down:                         50000.
Pages occupied by compressor:             10000.
"""


def test_parse_proc_stat():
    assert rl.parse_proc_stat(PROC_STAT) == (850, 1000)  # idle + iowait, total of 8 fields


def test_parse_meminfo_uses_available_memory():
    used, total = rl.parse_meminfo(MEMINFO)
    assert total == 16000 and used == 8000
    assert rl.parse_meminfo("MemTotal: 2048 kB\nMemFree: 1024 kB\n") == (1.0, 2.0)


def test_parse_top_and_vm_stat():
    assert rl.parse_top_mac("CPU usage: 5.2% user, 3.1% sys, 91.7% idle") == 8.3
    assert rl.parse_top_mac("nothing") is None
    used, total = rl.parse_vm_stat(VM_STAT, 16 * 1024**3)
    assert used == pytest.approx(160000 * 16384 / 1024 / 1024) and total == 16384


def test_simulator_is_repeatable_and_advances_time():
    first = rl.Simulator(datetime(2026, 11, 26, 9), 60)
    again = rl.Simulator(datetime(2026, 11, 26, 9), 60)
    rows = [first.sample() for _ in range(4)]
    assert rows == [again.sample() for _ in range(4)]
    assert [r["time"][11:] for r in rows] == ["09:00:00", "09:01:00", "09:02:00", "09:03:00"]
    assert rows[3]["cpu_percent"] > 30  # every fourth sample is a spike


def test_summary():
    rows = [{"cpu_percent": 10.0, "memory_percent": 50.0, "disk_percent": 70.0},
            {"cpu_percent": 30.0, "memory_percent": 60.0, "disk_percent": None}]
    lines = rl.summary(rows).splitlines()
    assert lines[0] == "cpu     min  10.0  avg  20.0  max  30.0"
    assert lines[2].startswith("disk    min  70.0")


def test_cli_simulated_csv_and_overwrite_rules(tmp_path, capsys):
    out = tmp_path / "log.csv"
    argv = ["--simulate", "--count", "3", "--interval", "30", "--start", "2026-11-26T09:00:00",
            "--output", str(out)]
    assert rl.main(argv) == 0
    text = capsys.readouterr().out
    assert "2026-11-26T09:00:30" in text and "Logged 3 sample(s)" in text and "cpu" in text
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["time"][-8:] for r in rows] == ["09:00:00", "09:00:30", "09:01:00"]
    assert list(rows[0]) == rl.FIELDS
    assert rl.main(argv) == 1  # refuses to overwrite
    assert "use --append" in capsys.readouterr().err
    assert rl.main([*argv, "--append", "--quiet"]) == 0
    capsys.readouterr()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 + 3 + 3 and lines.count(",".join(rl.FIELDS)) == 1  # one header only


def test_bad_arguments():
    for argv in (["--count", "0"], ["--interval", "-1"], ["--start", "tomorrow"]):
        with pytest.raises(SystemExit):
            rl.main(["--simulate", *argv])


def test_real_sampler_reads_this_machine(tmp_path):
    reading = rl.Sampler(str(tmp_path)).sample()
    assert list(reading) == rl.FIELDS
    assert 0 < reading["memory_percent"] <= 100 and 0 <= reading["disk_percent"] <= 100
    assert reading["cpu_percent"] is None or 0 <= reading["cpu_percent"] <= 100
