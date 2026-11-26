# wifi-info-reporter

## Purpose
Report which Wi-Fi network you are on and how good the connection is: signal percentage and dBm,
band, channel, security type and link speed. Handy for diagnosing a flaky connection or logging
Wi-Fi quality from a script.

## Install
No dependencies beyond Python 3.11+. It uses `netsh` on Windows, `nmcli` on Linux and the
`airport` tool on macOS.

## Usage
```
python wifi_info_reporter.py
python wifi_info_reporter.py --nearby                 # also list other networks (Linux)
python wifi_info_reporter.py --min-signal 40          # exit 1 if the signal is weaker than 40%
python wifi_info_reporter.py --format json
python wifi_info_reporter.py --from-file wifi.txt
```

- Signal is shown as a percentage with a word (`excellent` from 75%, `good` from 50%, `fair` from
  30%, otherwise `weak`). Where the system only gives a percentage the dBm value is estimated.
- The exit code is 1 when you are not connected or the signal is below `--min-signal`.
- `--from-file` reads saved `netsh wlan show interfaces`, `airport -I` or `nmcli -t` output.

## Example
`--from-file netsh-wlan.txt`

```
Network:   HomeNet-5G
Signal:    82% excellent (-59 dBm)
Band:      5 GHz
Channel:   44
Security:  WPA2-Personal
Speed:     866.7 Mbit/s
Radio:     802.11ax
BSSID:     aa:bb:cc:dd:ee:ff
```

## Notes
- macOS 14.4 and later removed the `airport` command, so live macOS reports aren't available
  there; use a saved report with `--from-file`.
- It only reads connection details. It never connects, disconnects or changes any setting.
- The SSID and BSSID identify your network, so think before posting the output publicly.
