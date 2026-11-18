# port-conflict-checker

## Purpose
Avoid the "port is already allocated" error when starting your services. Give the tool the ports you need (or a `docker-compose.yml`) and it reports two kinds of trouble: **duplicates**, where two services publish the same host port (it understands `"8000:80"`, `127.0.0.1:9090:9090`, ranges such as `6380-6382:6380-6382` and `/udp`), and **ports already in use** on this machine, found by trying to bind them.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python port_conflict_checker.py 8000 8080-8082
python port_conflict_checker.py --compose docker-compose.yml [--host 0.0.0.0] [--static]
```
Without `--static` each TCP port is also tested on this computer: `FREE` ports aren't listed as problems, `IN USE` means another program is listening, and `NO PERMISSION` means the port needs administrator rights (or, on Windows, is reserved). `--static` skips the machine check and only looks for duplicates. The exit code is 1 when any problem is found, so it works as a pre-flight check in scripts.

## Example
```bash
python port_conflict_checker.py --compose docker-compose.yml --static
```
```
5432/tcp DUPLICATE (docker-compose.yml:db and docker-compose.yml:cache) docker-compose.yml:cache, docker-compose.yml:db
   6380/tcp ok                                 docker-compose.yml:cache
   6381/tcp ok                                 docker-compose.yml:cache
   6382/tcp ok                                 docker-compose.yml:cache
   8000/tcp DUPLICATE (docker-compose.yml:web and docker-compose.yml:api) docker-compose.yml:api, docker-compose.yml:web
   8443/tcp ok                                 docker-compose.yml:web
   9090/tcp ok                                 docker-compose.yml:api

7 port(s) checked: 2 problem(s). Machine check skipped (--static).
```

## Notes
- Container-only ports (`"3000"` with no host side) are skipped because Docker picks a random host port.
- Binding a port briefly and releasing it is safe, but a service could still grab the port a moment later.
- Use `open-ports-lister` to see which programs are listening right now.
- The website demo runs the duplicate check only; testing ports works on your own computer.
