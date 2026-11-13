# ssh-key-auditor

## Purpose
Spot risky SSH keys before they become a problem. The tool reads your public keys, `authorized_keys` files and private key files and reports each key's type and length, its SHA-256 fingerprint and a verdict: **WEAK** for DSA keys and RSA keys under 2048 bits, a **NOTE** for RSA 2048 (fine, but ed25519 is better), and OK for ed25519, ECDSA, hardware-backed and RSA 3072+ keys. For private keys it checks whether a passphrase protects them and, on Linux and macOS, whether other users can read the file.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python ssh_key_auditor.py                 # audits ~/.ssh
python ssh_key_auditor.py ~/.ssh/authorized_keys /srv/keys [--max-age-days 365]
```
Give it files or folders (the default is `~/.ssh`; `known_hosts` and `config` are skipped). Private keys are only inspected, never uploaded or printed: the tool reads the first lines of the file to see whether it is encrypted, and ignores the secret part. `--max-age-days` adds a note for files not modified for a long time (keys don't record their creation date, so the file's date is used). The exit code is 1 when anything is WEAK. Nothing is changed; fix problems yourself, for example `ssh-keygen -t ed25519` to make a new key and `chmod 600 ~/.ssh/id_rsa` for permissions.

## Example
```bash
python ssh_key_auditor.py ssh-demo
```
```
authorized_keys
  [OK  ] ssh-ed25519 ed25519 - id_ed25519@demo-laptop SHA256:95Wqisu+3zXaqfBpDjPvxbSJnwQ4OjXu5PlT+2nZYGY
  [NOTE] ssh-rsa RSA 2048-bit is acceptable but ed25519 is stronger and shorter - id_rsa_old@demo-laptop SHA256:DeYxie+kyegwgks7q4FXv+gN87zwYIKBrNW5fxtPB7A
  [OK  ] ecdsa-sha2-nistp256 ECDSA 256-bit - id_ecdsa@demo-laptop SHA256:8iQjhsFtBy3a+K8JT5iJgI3nVgx4Ciok0Yj4mvnZksQ, restricted by options: command="/usr/bin/backup",no-pty,no-port-forwarding
  [WEAK] ssh-dss DSA keys are obsolete and disabled in modern OpenSSH; replace with ed25519 - old-dsa@legacy SHA256:p32g3tHJ4y5/WjuRASSkPcpZiFWwtshOcADtcTyUnsQ
id_dsa.pub
  [WEAK] ssh-dss DSA keys are obsolete and disabled in modern OpenSSH; replace with ed25519 - old-dsa@legacy SHA256:p32g3tHJ4y5/WjuRASSkPcpZiFWwtshOcADtcTyUnsQ
id_ecdsa.pub
  [OK  ] ecdsa-sha2-nistp256 ECDSA 256-bit - id_ecdsa@demo-laptop SHA256:8iQjhsFtBy3a+K8JT5iJgI3nVgx4Ciok0Yj4mvnZksQ
id_ed25519.pub
  [OK  ] ssh-ed25519 ed25519 - id_ed25519@demo-laptop SHA256:95Wqisu+3zXaqfBpDjPvxbSJnwQ4OjXu5PlT+2nZYGY
id_rsa.pub
  [OK  ] ssh-rsa RSA 4096-bit - id_rsa@demo-laptop SHA256:rdkCKsDiavsXATZgMUUN3aQH2A1Q9S3IgMywDsGn2nw
id_rsa_old.pub
  [NOTE] ssh-rsa RSA 2048-bit is acceptable but ed25519 is stronger and shorter - id_rsa_old@demo-laptop SHA256:DeYxie+kyegwgks7q4FXv+gN87zwYIKBrNW5fxtPB7A
id_rsa_pem
  [OK  ] private key is passphrase-protected
priv_locked
  [OK  ] private key is passphrase-protected
priv_plain
  [WEAK] private key has NO passphrase - anyone who copies it can use it

12 item(s) reviewed: 3 weak, 2 note(s). Nothing was changed.
```

## Notes
- The example folder holds sample public keys and truncated fake private-key files; none of them is usable.
- A key with options such as `command="..."` or `no-pty` in `authorized_keys` is shown with those restrictions.
- On Windows, file permissions work differently, so the permission check is skipped.
