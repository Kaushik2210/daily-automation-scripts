import contextlib
import os
import subprocess
import sys
import time

import process_cleaner as pc
import pytest

PS = """  1 86400 00:01:10 12000 systemd
  812 86000 00:00:12 9800 sshd
 1044 86000 00:03:20 7400 nginx
 1051 85990 00:12:45 52000 nginx
 1052 85000 00:11:02 51000 nginx
 1053    30 00:00:01 49500 nginx
 3301  7200 01:55:00 1850000 python
 6001  9000 02:30:00 95000 stuck-worker
"""


def procs():
    return pc.parse_ps(PS)


def names(chosen):
    return [(p["pid"], p["reason"].split(":")[0]) for p in chosen]


def test_parse_powershell_with_and_without_age():
    text = ('"Id","ProcessName","CPU","WorkingSet64","Age"\n'
            '"900","node","12.5","104857600","3600.5"\n"4","System","","147456",""\n')
    found = pc.parse_powershell(text)
    assert found[0]["age"] == 3600.5 and found[0]["mem_mb"] == 100 and found[1]["age"] is None


def test_matches_ignores_case_and_exe():
    assert pc.matches("Node.EXE", ["node"]) and pc.matches("python3", ["py*"])
    assert not pc.matches("nodejs", ["node"])


def test_duplicates_keep_the_oldest():
    chosen, _ = pc.plan(procs(), ["nginx"], 1, True, None, None, 0, set())
    assert [p["pid"] for p in chosen] == [1051, 1052, 1053]  # 1044 is the oldest, so it is kept
    assert chosen[0]["reason"] == "duplicate: instance 2 of 4 (keeping the oldest 1)"
    two, _ = pc.plan(procs(), ["nginx"], 2, True, None, None, 0, set())
    assert sorted(p["pid"] for p in two) == [1052, 1053]


def test_runaway_by_memory_and_average_cpu_with_min_age():
    chosen, _ = pc.plan(procs(), ["python", "stuck*", "nginx"], 1, False, 90, 1000, 60, set())
    reasons = {p["pid"]: p["reason"] for p in chosen}
    assert set(reasons) == {3301, 6001}
    assert reasons[3301] == ("runaway: averaging 96% CPU since it started; "
                             "runaway: using 1807 MB")  # both rules are reported
    assert "averaging 100% CPU" in reasons[6001]  # 9000 s of CPU in 9000 s
    assert 1053 not in reasons  # too young to judge


def test_protected_and_own_processes_are_never_selected():
    chosen, skipped = pc.plan(procs(), ["systemd", "sshd", "nginx"], 1, True, None, None, 0,
                              {1051})
    assert 1051 not in [p["pid"] for p in chosen]
    why = {p["pid"]: p["why"] for p in skipped}
    assert why[1] == "protected system process" and why[812] == "protected system process"
    assert why[1051] == "this tool or its parent"
    assert pc.plan([{"pid": 3, "name": "odd", "age": 9, "cpu_s": 0, "mem_mb": 1}],
                   ["odd"], 1, True, None, 0, 0, set())[0] == []  # tiny pids are system pids


def test_a_process_matching_both_rules_is_listed_once():
    chosen, _ = pc.plan(procs(), ["nginx"], 1, True, None, 40, 0, set())
    assert [p["pid"] for p in chosen].count(1051) == 1


def test_stop_is_polite_first():
    calls, alive = [], iter([True, True, False])
    outcome = pc.stop(7, 5, False, lambda pid, force: calls.append(force),
                      lambda pid: next(alive), lambda s: None)
    assert outcome == "stopped" and calls == [False]  # never forced


def test_stop_only_forces_when_asked():
    calls = []
    stubborn = {"terminate": lambda pid, force: calls.append(force),
                "alive": lambda pid: True, "sleep": lambda s: None}
    assert pc.stop(7, 0.5, False, **stubborn).startswith("still running")
    assert calls == [False]
    calls.clear()
    assert pc.stop(7, 0.5, True, **stubborn) == "could not be stopped"
    assert calls == [False, True]
    flags = iter([True, True, False])
    killed = pc.stop(7, 0.25, True, lambda pid, force: None, lambda pid: next(flags),
                     lambda s: None)
    assert killed == "killed"


def test_a_refused_polite_request_falls_through_to_force():
    def refuse_politely(pid, force):
        if not force:
            raise OSError("This process can only be terminated forcefully")

    state = {"alive": True}

    def kill_it(pid, force):
        refuse_politely(pid, force)
        state["alive"] = False

    assert pc.stop(7, 5, True, kill_it, lambda pid: state["alive"], lambda s: None) == "killed"
    state["alive"] = True
    assert pc.stop(7, 5, False, kill_it, lambda pid: state["alive"], lambda s: None).startswith(
        "still running")


def test_cli_dry_run_changes_nothing(tmp_path, capsys):
    saved = tmp_path / "ps.txt"
    saved.write_text(PS)
    assert pc.main(["nginx", "systemd", "--duplicates", "--min-age", "0", "--from-file",
                    str(saved)]) == 0
    out = capsys.readouterr().out
    assert "would stop" in out and "1052" in out and "protected system process" in out
    assert "Dry run: 3 process(es) would be stopped" in out
    assert pc.main(["nothing-matches", "--duplicates", "--from-file", str(saved)]) == 0
    assert "Nothing to stop." in capsys.readouterr().out


def test_cli_argument_rules(tmp_path):
    saved = tmp_path / "ps.txt"
    saved.write_text(PS)
    for argv in (["nginx"], ["nginx", "--duplicates", "--keep", "0"],
                 ["nginx", "--duplicates", "--apply", "--from-file", str(saved)],
                 ["nginx", "--mem-over", "5", "--grace", "-1"]):
        with pytest.raises(SystemExit):
            pc.main(argv)
    with pytest.raises(SystemExit):  # names are required: it never acts on "everything"
        pc.main(["--duplicates"])
    assert pc.main(["x", "--duplicates", "--from-file", str(tmp_path / "none")]) == 1


def test_really_stops_only_the_extra_copies(monkeypatch, capsys):
    """Start three real sleeping processes and stop the two youngest through the CLI."""
    sleepers = []
    try:
        for _ in range(3):
            sleepers.append(subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(120)"]))
            time.sleep(1.2)  # distinct ages
        spawned = {p.pid for p in sleepers}
        real_list = pc.list_processes
        monkeypatch.setattr(pc, "list_processes",
                            lambda: [p for p in real_list() if p["pid"] in spawned])
        name = next(p["name"] for p in pc.list_processes())
        code = pc.main([name, "--duplicates", "--min-age", "0", "--grace", "3", "--force",
                        "--apply"])
        out = capsys.readouterr().out
        for proc in sleepers:
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=0.2)
        assert code == 0, out
        assert out.count("stopped") + out.count("killed") == 2, out
        assert sleepers[0].poll() is None  # the oldest copy is still running
        assert sleepers[1].poll() is not None and sleepers[2].poll() is not None
    finally:
        for proc in sleepers:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
    assert os.getpid() not in {p.pid for p in sleepers}
