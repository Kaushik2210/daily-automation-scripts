import json
from types import SimpleNamespace

import pytest
import wifi_info_reporter as wir

NETSH = """There is 1 interface on the system:

    Name                   : Wi-Fi
    State                  : connected
    SSID                   : HomeNet-5G
    BSSID                  : aa:bb:cc:dd:ee:ff
    Radio type             : 802.11ax
    Authentication         : WPA2-Personal
    Channel                : 44
    Receive rate (Mbps)    : 866.7
    Signal                 : 82%
"""
NETSH_DOWN = "    Name   : Wi-Fi\n    State  : disconnected\n"
AIRPORT = """     agrCtlRSSI: -61
    agrCtlNoise: -92
        lastTxRate: 585
      link auth: wpa2-psk
          BSSID: aa:bb:cc:dd:ee:ff
           SSID: StudioWiFi
        channel: 149,80
"""
NMCLI = ("no:OfficeGuest:64:6:2437 MHz:WPA2\n"
         "yes:Cafe\\: Main:41:36:5180 MHz:WPA2 WPA3\n"
         "no:Neighbour:28:1:2412 MHz:\n")


@pytest.mark.parametrize("rssi,percent", [(-100, 0), (-75, 50), (-50, 100), (-30, 100), (-120, 0)])
def test_rssi_percent_conversions(rssi, percent):
    assert wir.rssi_to_percent(rssi) == percent
    assert wir.percent_to_rssi(50) == -75 and wir.percent_to_rssi(100) == -50


def test_quality_and_band():
    assert [wir.quality(p) for p in (90, 75, 60, 35, 10)] == [
        "excellent", "excellent", "good", "fair", "weak"]
    assert wir.band(channel=6) == "2.4 GHz" and wir.band(channel=44) == "5 GHz"
    assert wir.band(mhz=5180) == "5 GHz" and wir.band(mhz=6115) == "6 GHz" and wir.band() is None


def test_parse_netsh():
    wifi = wir.parse_netsh(NETSH)
    assert (wifi["ssid"], wifi["signal_percent"], wifi["channel"]) == ("HomeNet-5G", 82, 44)
    assert wifi["band"] == "5 GHz" and wifi["rate_mbps"] == 866.7 and wifi["rssi_dbm"] == -59
    assert wifi["bssid"] == "aa:bb:cc:dd:ee:ff"  # first colon only splits the key
    assert wir.parse_netsh(NETSH_DOWN) is None


def test_parse_airport():
    wifi = wir.parse_airport(AIRPORT)
    assert wifi["ssid"] == "StudioWiFi" and wifi["rssi_dbm"] == -61
    assert wifi["signal_percent"] == 78 and wifi["channel"] == 149 and wifi["noise_dbm"] == -92
    assert wifi["rate_mbps"] == 585 and wir.parse_airport("AirPort: Off") is None


def test_parse_nmcli_handles_escaped_colons_and_open_networks():
    networks = wir.parse_nmcli(NMCLI)
    assert [n["ssid"] for n in networks] == ["OfficeGuest", "Cafe: Main", "Neighbour"]
    assert networks[1]["active"] and networks[1]["band"] == "5 GHz"
    assert networks[2]["security"] == "open" and networks[0]["band"] == "2.4 GHz"


def test_parse_any_picks_the_format():
    assert wir.parse_any(NETSH)[0]["ssid"] == "HomeNet-5G"
    assert wir.parse_any(AIRPORT)[0]["ssid"] == "StudioWiFi"
    current, others = wir.parse_any(NMCLI)
    assert current["ssid"] == "Cafe: Main" and len(others) == 2
    assert wir.parse_any("")[0] is None


def test_read_system_chooses_commands_and_reports_failures():
    seen = []

    def fake(command, **kwargs):
        seen.append(command[0])
        return SimpleNamespace(returncode=0, stdout="x", stderr="")

    assert wir.read_system(fake, "Windows") == "x" and wir.read_system(fake, "Linux") == "x"
    assert seen == ["netsh", "nmcli"]

    def failing(command, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="NetworkManager is not running")

    with pytest.raises(OSError, match="NetworkManager"):
        wir.read_system(failing, "Linux")

    def missing(command, **kwargs):
        raise FileNotFoundError

    with pytest.raises(OSError, match="not installed"):
        wir.read_system(missing, "Linux")


def test_cli_outputs(tmp_path, capsys):
    saved = tmp_path / "w.txt"
    saved.write_text(NETSH)
    assert wir.main(["--from-file", str(saved)]) == 0
    out = capsys.readouterr().out
    assert "Network:   HomeNet-5G" in out and "Signal:    82% excellent (-59 dBm)" in out
    assert "Speed:     866.7 Mbit/s" in out and "Band:      5 GHz" in out
    assert wir.main(["--from-file", str(saved), "--min-signal", "90"]) == 1
    assert "below the 90% minimum" in capsys.readouterr().err
    saved.write_text(NMCLI)
    assert wir.main(["--from-file", str(saved), "--nearby"]) == 0
    out = capsys.readouterr().out
    assert "Nearby networks:" in out and out.index("OfficeGuest") < out.index("Neighbour")
    assert wir.main(["--from-file", str(saved), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["current"]["ssid"] == "Cafe: Main"


def test_cli_when_not_connected_or_unreadable(tmp_path, capsys):
    saved = tmp_path / "w.txt"
    saved.write_text(NETSH_DOWN)
    assert wir.main(["--from-file", str(saved)]) == 1
    assert "Not connected" in capsys.readouterr().out
    assert wir.main(["--from-file", str(tmp_path / "none.txt")]) == 1
    assert "Can't read the Wi-Fi details" in capsys.readouterr().err
