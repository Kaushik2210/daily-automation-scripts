# dockerfile-linter

## Purpose
Catch the Dockerfile mistakes that cause slow builds, big images and security problems, before you build. The linter reads your Dockerfile (including multi-line `RUN` commands) and flags: images with no tag or `:latest`, a container that runs as root, `apt-get install` without `-y`, missing cache cleanup, `pip install` without `--no-cache-dir`, `ADD` where `COPY` is meant, `cd` instead of `WORKDIR`, relative `WORKDIR`, `sudo`, `curl ... | sh`, secrets such as `ENV ADMIN_PASSWORD=...`, port 22, duplicate `CMD`/`ENTRYPOINT`, a missing `HEALTHCHECK`, and copying all source before installing dependencies (which defeats layer caching).

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python dockerfile_linter.py Dockerfile [--strict] [--ignore DL012,DL014]
```
Each finding shows the line number, a severity (ERROR, WARN or INFO), a rule id and a plain explanation. The exit code is 1 when there is any ERROR; with `--strict` warnings fail too. `--ignore` skips rules you disagree with.

## Example
```bash
python dockerfile_linter.py Dockerfile
```
```
Dockerfile:1  WARN  DL001  'ubuntu' has no tag, so it means :latest; pin a version
Dockerfile:1  WARN  DL002  No USER instruction: the container runs as root
Dockerfile:1  INFO  DL012  No HEALTHCHECK defined
Dockerfile:3  ERROR DL004  apt-get install without -y waits for input and fails
Dockerfile:3  WARN  DL004  Remove /var/lib/apt/lists/* in the same RUN
Dockerfile:3  WARN  DL004  Run 'apt-get update' in the same RUN as install
Dockerfile:3  INFO  DL004  Add --no-install-recommends to keep the image smaller
Dockerfile:4  ERROR DL011  ADMIN_PASSWORD looks like a secret baked into the image
Dockerfile:5  WARN  DL013  WORKDIR 'app' is relative; use an absolute path
Dockerfile:6  WARN  DL003  Use COPY instead of ADD for plain files (ADD has hidden extras)
Dockerfile:7  WARN  DL005  pip install without --no-cache-dir keeps its cache
Dockerfile:7  WARN  DL006  Use WORKDIR instead of 'cd' inside RUN
Dockerfile:8  ERROR DL009  Piping a download into a shell runs unverified code
Dockerfile:9  WARN  DL010  Port 22 suggests SSH in a container; use docker exec instead
Dockerfile:11  WARN  DL007  2 CMD instructions; only the last one has an effect

3 error(s), 10 warning(s), 2 suggestion(s).
```

## Notes
- Only the last stage of a multi-stage build is checked for `USER`.
- This is a quick static check, not a replacement for a full tool like hadolint or a vulnerability scanner.
- Use `env-template-generator` to keep secrets out of files you commit.
