# permission-auditor

## Purpose
Spot permission mistakes that quietly open up your files on Linux and macOS: files anyone can write, shared folders missing the sticky bit, setuid/setgid programs, and private keys (SSH keys, `.pem`, `.key`) that other users can read.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python permission_auditor.py [FOLDER] [--apply]
```
Dry run by default: it lists each issue with the current and the safer mode. Pass `--apply` to change the permissions. On Windows, which has no Unix permission bits, it explains that and exits cleanly.

## Example
```bash
python permission_auditor.py ~/.ssh
```
```
0644 -> 0600  private key readable by others: /home/me/.ssh/id_ed25519
Would fix 1 issue(s).
Use --apply to do it.
```

## Notes
- Fixes only remove the risky bit (for example `o-w`) or restrict keys to the owner; they never add permissions.
- Symlinks are not followed, and `.git` and `node_modules` are skipped.
- Always review the dry-run list first. Some programs, such as `sudo`, are meant to be setuid.
