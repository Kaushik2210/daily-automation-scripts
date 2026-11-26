import json
import plistlib

import startup_lister as sl

DESKTOP = """# comment
[Desktop Entry]
Type=Application
Name=Slack
Exec=/usr/bin/slack --startup
[Desktop Action new]
Name=Not this one
"""


def make_root(tmp_path):
    auto = tmp_path / ".config/autostart"
    auto.mkdir(parents=True)
    (auto / "slack.desktop").write_text(DESKTOP)
    (auto / "old.desktop").write_text("[Desktop Entry]\nName=Old\nExec=/opt/old\nHidden=true\n")
    (auto / "off.desktop").write_text(
        "[Desktop Entry]\nName=Off\nExec=/opt/off\nX-GNOME-Autostart-enabled=false\n")
    agents = tmp_path / "Library/LaunchAgents"
    agents.mkdir(parents=True)
    (agents / "sync.plist").write_bytes(plistlib.dumps(
        {"Label": "com.example.sync", "ProgramArguments": ["/usr/local/bin/sync", "--daemon"],
         "RunAtLoad": True}))
    (agents / "manual.plist").write_bytes(plistlib.dumps(
        {"Label": "com.example.manual", "Program": "/usr/local/bin/manual"}))
    (agents / "broken.plist").write_text("not a plist")
    startup = tmp_path / "Startup"
    startup.mkdir()
    (startup / "OneDrive.cmd").write_text("@echo off")
    (startup / "notes.txt").write_text("ignored")
    return tmp_path


def test_parse_desktop_reads_only_the_entry_section():
    values = sl.parse_desktop(DESKTOP)
    assert values["Name"] == "Slack" and values["Exec"] == "/usr/bin/slack --startup"
    assert "Type" in values and len(values) == 3


def test_scan_root_finds_each_kind(tmp_path):
    items = sl.scan_root(make_root(tmp_path))
    by_name = {i["name"]: i for i in items}
    assert set(by_name) == {"Slack", "Old", "Off", "com.example.sync", "com.example.manual",
                            "OneDrive"}
    assert by_name["Slack"]["enabled"] and not by_name["Old"]["enabled"]
    assert not by_name["Off"]["enabled"]
    assert by_name["com.example.sync"]["command"] == "/usr/local/bin/sync --daemon"
    assert by_name["com.example.sync"]["enabled"] and not by_name["com.example.manual"]["enabled"]
    assert by_name["com.example.manual"]["command"] == "/usr/local/bin/manual"
    assert by_name["OneDrive"]["source"] == "startup folder"
    assert sl.scan_root(tmp_path / "nothing-here") == []


class FakeWinreg:
    HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE = "HKCU-handle", "HKLM-handle"

    class Key:
        def __init__(self, values):
            self.values = values

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    data = {("HKCU-handle", r"Software\Microsoft\Windows\CurrentVersion\Run"):
            [("Spotify", r"C:\Users\me\AppData\Roaming\Spotify\Spotify.exe --minimized", 1),
             ("Updater", r"C:\Users\me\AppData\Local\Temp\upd.exe", 1)]}

    def OpenKey(self, root, subkey):  # noqa: N802 (mirrors winreg)
        if (root, subkey) not in self.data:
            raise FileNotFoundError(subkey)
        return self.Key(self.data[(root, subkey)])

    def EnumValue(self, key, index):  # noqa: N802
        if index >= len(key.values):
            raise OSError("no more data")
        return key.values[index]


def test_read_run_keys_with_a_fake_registry():
    items = sl.read_run_keys(FakeWinreg())
    assert [i["name"] for i in items] == ["Spotify", "Updater"]
    assert items[0]["source"] == "registry HKCU\\Run" and "Spotify.exe" in items[0]["command"]


def test_risky_locations():
    assert sl.is_risky(r"C:\Users\me\AppData\Local\Temp\upd.exe")
    assert sl.is_risky("/home/me/Downloads/tool") and sl.is_risky("/tmp/x.sh")
    assert not sl.is_risky(r"C:\Program Files\App\app.exe")


def test_cli_text_json_csv(tmp_path, capsys):
    root = make_root(tmp_path)
    assert sl.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "autostart (desktop) (3)" in out and "Slack: /usr/bin/slack --startup" in out
    assert "Old: /opt/old  [disabled]" in out and "6 item(s), 3 enabled, 3 disabled." in out
    assert sl.main(["--root", str(root), "--only-enabled", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert sorted(i["name"] for i in data) == ["OneDrive", "Slack", "com.example.sync"]
    assert sl.main(["--root", str(root), "--format", "csv"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "source,name,command,enabled,risky,location" and len(lines) == 7


def test_cli_errors_and_empty(tmp_path, capsys):
    assert sl.main(["--root", str(tmp_path / "missing")]) == 1
    assert "Not a folder" in capsys.readouterr().err
    assert sl.main(["--root", str(tmp_path)]) == 0
    assert "No startup items found." in capsys.readouterr().out


def test_scanning_the_real_system_does_not_crash():
    items = sl.scan_system()
    assert isinstance(items, list)
    assert all({"source", "name", "command", "enabled", "location"} <= set(i) for i in items)
