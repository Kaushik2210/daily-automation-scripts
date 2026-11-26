# process-cleaner

## Purpose
Stop processes that pile up or run away: extra copies of the same program (for example five
stray `node` dev servers) and processes that use too much memory or have been hogging CPU. It
shows exactly what it would stop first, and only acts when you add `--apply`.

## Install
No dependencies beyond Python 3.11+. It uses `ps` on Linux and macOS, and PowerShell and
`taskkill` on Windows.

## Usage
```
python process_cleaner.py node --duplicates                  # show the plan (nothing is stopped)
python process_cleaner.py node --duplicates --apply          # keep the oldest, stop the rest
python process_cleaner.py "python*" --mem-over 2000 --apply  # anything over 2 GB
python process_cleaner.py ffmpeg --cpu-over 90 --min-age 300 --apply
python process_cleaner.py chrome --duplicates --keep 5 --force --apply
python process_cleaner.py nginx --duplicates --from-file ps.txt
```

Safety rules built in:
- You must name the programs (exact names or patterns like `python*`) and say what to look for
  (`--duplicates`, `--cpu-over` or `--mem-over`). It never acts on "everything".
- System processes (`systemd`, `explorer`, `svchost`, `sshd`, `launchd` and similar), the first few
  process ids, and this tool and its parent are always skipped.
- Processes younger than `--min-age` seconds (60) are ignored for the runaway checks.
- `--apply` first asks each process to quit and waits `--grace` seconds (5). Only with `--force`
  does it kill one that ignores the request. Some Windows console programs refuse the polite
  request, so they need `--force`.
- `--cpu-over` is the average CPU use over the process's whole life, since a one-off sample is
  noisy. `--duplicates` keeps the oldest `--keep` copies.

## Example
`nginx systemd --duplicates --min-age 0 --from-file ps-snapshot.txt`

```
skip        1  systemd  (protected system process)
would stop    1051  nginx                   51 MB  duplicate: instance 2 of 4 (keeping the oldest 1)
would stop    1052  nginx                   50 MB  duplicate: instance 3 of 4 (keeping the oldest 1)
would stop    1053  nginx                   48 MB  duplicate: instance 4 of 4 (keeping the oldest 1)

Dry run: 3 process(es) would be stopped. Add --apply to do it.
```

## Notes
- Be careful with programs that legitimately run many copies (browsers, `svchost`, build workers).
  Read the dry-run output before using `--apply`.
- Stopping a process loses any unsaved work in it.
- `--from-file` only prints a plan; `--apply` needs the live system.
