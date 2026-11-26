import json
from pathlib import Path
from types import SimpleNamespace

import battery_reporter as br
import pytest


def make_bat(root, **files):
    folder = root / "BAT0"
    folder.mkdir(parents=True)
    for name, value in files.items():
        (folder / name).write_text(f"{value}\n")
    return root


SYSFS = {"status": "Discharging", "capacity": "74", "energy_full": "41200000",
         "energy_full_design": "50000000", "energy_now": "30488000", "cycle_count": "312",
         "technology": "Li-ion", "manufacturer": "SMP", "model_name": "DELL 7XFMD",
         "power_now": "8400000"}

IOREG = """    | |   "MaxCapacity" = 100
    | |   "DesignCapacity" = 5000
    | |   "AppleRawMaxCapacity" = 4400
    | |   "AppleRawCurrentCapacity" = 2200
    | |   "CycleCount" = 421
    | |   "IsCharging" = No
    | |   "ExternalConnected" = No
"""

POWERCFG = """<?xml version="1.0"?>
<BatteryReport xmlns="http://schemas.microsoft.com/battery/2012">
  <Batteries><Battery><Id>X</Id><Manufacturer>LGC</Manufacturer>
    <DesignCapacity>50000</DesignCapacity><FullChargeCapacity>38000</FullChargeCapacity>
    <CycleCount>250</CycleCount></Battery></Batteries>
</BatteryReport>"""


def test_health_labels():
    worn = "worn: consider a replacement"
    assert [br.health_label(h) for h in (95, 80, 79.9, 60, 59, None)] == [
        "good", "good", "fair", "fair", worn, "unknown"]


def test_build_computes_health_and_time_left():
    report = br.build(50, "Discharging", 50000, 40000, now=20000, watts=10.0)
    assert report["health_percent"] == 80.0 and report["health"] == "good"
    assert report["hours_remaining"] == 2.0  # 20000 mWh / 10 W
    assert br.build(50, "Charging", 50000, 40000, now=20000, watts=10)["hours_remaining"] is None
    assert br.build(None, None, None, None)["health_percent"] is None


def test_read_sysfs(tmp_path):
    report = br.read_sysfs(make_bat(tmp_path, **SYSFS))
    assert report["percent"] == 74 and report["status"] == "Discharging"
    assert report["health_percent"] == 82.4 and report["cycles"] == 312
    assert report["model"] == "SMP DELL 7XFMD" and report["power_watts"] == 8.4
    assert report["hours_remaining"] == 3.6  # 30488 mWh / 8.4 W


def test_read_sysfs_charge_units_and_missing_capacity(tmp_path):
    root = make_bat(tmp_path, status="Charging", charge_full="3000000",
                    charge_full_design="4000000", charge_now="1500000")
    report = br.read_sysfs(root)
    assert report["percent"] == 50 and report["health_percent"] == 75.0
    assert br.read_sysfs(tmp_path / "nothing") is None
    (tmp_path / "empty").mkdir()
    assert br.read_sysfs(tmp_path / "empty") is None


def test_parse_ioreg():
    report = br.parse_ioreg(IOREG)
    assert report["health_percent"] == 88.0 and report["cycles"] == 421
    assert report["percent"] == 50 and report["status"] == "Discharging"
    assert br.parse_ioreg("nothing useful") is None
    assert br.parse_ioreg(IOREG.replace('"IsCharging" = No', '"IsCharging" = Yes'))[
        "status"] == "Charging"


def test_parse_powercfg_xml():
    report = br.parse_powercfg_xml(POWERCFG, 63, "Discharging")
    assert report["health_percent"] == 76.0 and report["cycles"] == 250
    assert report["model"] == "LGC" and report["percent"] == 63
    assert br.parse_powercfg_xml("<BatteryReport/>") is None


def test_read_windows_uses_powershell_and_powercfg(tmp_path):
    calls = []

    def fake(command, **kwargs):
        calls.append(command[0])
        if command[0] == "powershell":
            return SimpleNamespace(returncode=0, stdout="[63, 1]", stderr="")
        Path(command[3]).write_text(POWERCFG, encoding="utf-8")  # powercfg writes the report
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    report = br.read_windows(fake)
    assert calls == ["powershell", "powercfg"]
    assert report["percent"] == 63 and report["status"] == "Discharging"
    assert report["health_percent"] == 76.0

    def no_battery(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    assert br.read_windows(no_battery) is None


def test_summarise_history(tmp_path):
    path = tmp_path / "h.csv"
    path.write_text("time,percent,status,health\n"
                    "2026-11-01T09:00:00,80,Discharging,84.0\n"
                    "2026-11-16T09:00:00,15,Discharging,83.0\n"
                    "2026-12-01T09:00:00,55,Charging,82.0\n")
    text = br.summarise_history(path)
    assert "3 reading(s), 2026-11-01 to 2026-12-01" in text
    assert "lowest 15%, highest 80%, average 50%" in text
    assert "84.0% -> 82.0% (+2.00 points lost per 30 days)" in text
    assert "at or below 20%: 1 of 3" in text
    empty = tmp_path / "e.csv"
    empty.write_text("time,percent,status,health\n")
    with pytest.raises(ValueError):
        br.summarise_history(empty)


def test_cli_report_log_and_minimum(tmp_path, capsys):
    root = make_bat(tmp_path / "ps", **SYSFS)
    log = tmp_path / "log.csv"
    assert br.main(["--sysfs", str(root), "--log", str(log)]) == 0
    out = capsys.readouterr()
    assert "Charge:    74% (Discharging)" in out.out and "Health:    82.4%" in out.out
    assert "Time left: 3.6 h" in out.out and "Logged to" in out.err
    assert br.main(["--sysfs", str(root), "--log", str(log), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["cycles"] == 312
    assert len(log.read_text().splitlines()) == 3  # one header, two readings
    assert br.main(["--sysfs", str(root), "--min-health", "90"]) == 1
    assert "below the 90% minimum" in capsys.readouterr().err
    assert br.main(["--history", str(log)]) == 0
    assert "History: 2 reading(s)" in capsys.readouterr().out


def test_cli_without_a_battery(tmp_path, capsys):
    assert br.main(["--sysfs", str(tmp_path)]) == 1
    assert "No battery found" in capsys.readouterr().err
    assert br.main(["--history", str(tmp_path / "none.csv")]) == 1
