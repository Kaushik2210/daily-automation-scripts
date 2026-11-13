# port-scanner

## Purpose
See which network services a machine is offering. The tool tries a TCP connection to each port you choose and reports the ones that answer, with the service normally found there (ssh, https, postgresql...) and a warning for ports that are risky to leave open, such as Telnet, Redis or an unprotected Docker API. It is meant for your own computer, your home network and servers you administer.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python port_scanner.py [HOST] [--ports 22,80,443 | 1-1024 | common] [--banner] [--timeout 0.5] [--threads 100]
python port_scanner.py --ports common --explain
```
With no host it scans `127.0.0.1`. `--ports common` (the default) tries about fifty well-known ports; ranges like `1-1024` and lists like `22,80,8000-8100` work too. `--banner` shows the first line a service sends, which often reveals its software and version. By default only loopback and private (LAN) addresses are scanned. A public address is refused unless you add `--i-own-this`, confirming that it is yours or that you have written permission: scanning other people's machines can be illegal and will be noticed. `--explain` just describes the ports without scanning anything.

## Example
```bash
python port_scanner.py --ports 22,23,80,443,3306,6379,27017 --explain
```
```
   22  ssh
   23  telnet   ! telnet sends passwords in clear text
   80  http
  443  https
 3306  mysql
 6379  redis   ! Redis is often left open without a password
27017  mongodb   ! check that MongoDB requires authentication
```

## Notes
- This is a plain "connect" scan: it completes a normal TCP connection and then closes it. UDP ports and stealth techniques are deliberately not included.
- A port that doesn't answer is either closed or filtered by a firewall; the tool can't tell which.
- The limit is 500 parallel connections and 10 seconds per port, so a scan can't be turned into a flood.
- The website demo can only use `--explain`; scanning needs a real network and works on your own computer.
