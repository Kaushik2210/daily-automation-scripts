# open-ports-lister

## Purpose
Know what your computer is offering to the network. The tool lists every TCP (and on Windows and Linux, UDP) port the machine is listening on, the program that owns it, and whether it can be reached only from this computer or from other machines on the network. Risky services that are reachable from outside, such as a database, Redis, RDP or SMB, are flagged. It works on Windows, macOS and Linux by running the system's own read-only tools.

## Install
Standard library only, Python 3.11+. Nothing to install. It uses `netstat` and `tasklist` on Windows, `lsof` on macOS and `ss` on Linux, which are normally already there.

## Usage
```bash
python open_ports_lister.py [--only-exposed]
python open_ports_lister.py --parse saved-output.txt
```
Ports bound to `127.0.0.1` or `::1` are "this computer" only; `0.0.0.0` and `::` mean every network interface, and a specific address such as `192.168.1.20` is reachable on that network. `--only-exposed` hides the local-only ones. On Linux and macOS, run it with `sudo` to see the program names of other users' services. `--parse` reads saved output of `netstat -ano` (Windows), `ss -ltnup` (Linux) or `lsof -nP -iTCP -sTCP:LISTEN` (macOS) from a file, for example one collected on a server you can't run Python on. Nothing is changed.

## Example
```bash
python open_ports_lister.py --parse ss.txt
```
```
 Port  Proto  Reachable from    Service       Program
   22  tcp    all interfaces    ssh           sshd (pid 812)
   80  tcp    all interfaces    http          nginx (pid 1044)
  443  tcp    all interfaces    https         nginx (pid 1044)
 3306  tcp    all interfaces    mysql         mysqld (pid 1200)   <-- risky to expose
 5432  tcp    this computer     postgresql    postgres (pid 990)
 6379  tcp    this computer     redis         redis-server (pid 1010)

6 listening port(s): 4 reachable from other computers, 2 local only.
1 exposed service(s) are usually better kept local or behind a firewall.
```

## Notes
- Being reachable on the network doesn't mean reachable from the internet: your router and firewall still sit in between.
- Combine with `port-scanner` to see the same ports from the outside.
- The website demo reads the saved listings; listing real ports works on your own computer.
