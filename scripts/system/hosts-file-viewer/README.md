# hosts-file-viewer

## Purpose
Read the hosts file without squinting at raw text. Shows each entry's address, names and note, hides disabled lines unless you ask, and warns when the same name points at two different addresses.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python hosts_file_viewer.py [--file PATH] [--search TEXT] [--all]
```
By default it reads `/etc/hosts`, or `C:\Windows\System32\drivers\etc\hosts` on Windows.

## Example
```bash
python hosts_file_viewer.py --search nas
```
```
line  address           names                                   note
   6  192.168.1.5       nas.local, nas
   8  10.0.0.1          nas.local
2 entries from /etc/hosts.
Warning: names pointing to different addresses: nas.local
```

## Notes
- Read-only. Editing the hosts file needs administrator rights and is not done here.
- Lines starting with `#` are treated as disabled entries only when they look like `IP name`.
