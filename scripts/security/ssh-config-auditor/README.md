# ssh-config-auditor

## Purpose
Review your `~/.ssh/config` (or a server's `sshd_config`) for settings that weaken SSH, and get
an explanation of why each one matters and how to fix it: turned-off host key checks, agent
forwarding to every host, password logins, obsolete ciphers and key types, root login and more.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python ssh_config_auditor.py                          # reviews ~/.ssh/config
python ssh_config_auditor.py ~/work/ssh_config
python ssh_config_auditor.py /etc/ssh/sshd_config --server
python ssh_config_auditor.py --check-files            # also check IdentityFile permissions
python ssh_config_auditor.py --min-severity high --format json
python ssh_config_auditor.py --fail-on high           # exit 1 if anything is high or critical
```

Each finding shows its severity (`critical`, `high`, `medium`, `low`), the line, the `Host` or
`Match` block it sits in, and what to change. A few examples of what is checked:

| Setting | Why it is flagged |
|---|---|
| `StrictHostKeyChecking no`, `UserKnownHostsFile /dev/null` | lets anyone impersonate a server unnoticed |
| `ForwardAgent yes` | a compromised server can use your keys; worse under `Host *` |
| `PasswordAuthentication yes` | passwords can be guessed or phished |
| `Ciphers`, `MACs`, `KexAlgorithms`, `HostKeyAlgorithms` | weak entries such as `3des-cbc`, `arcfour`, `hmac-md5`, `ssh-rsa`, `ssh-dss` |
| `Protocol 1` | broken protocol version |
| `ForwardX11 yes`, `ForwardX11Trusted yes` | remote programs can watch your display and keystrokes |
| (server) `PermitRootLogin yes`, `PermitEmptyPasswords yes` | direct root or password-less access |

- Removing a weak algorithm with a leading `-` is recognised as a good thing, not flagged.
- `Include` lines are listed but not followed; audit those files too.
- `--check-files` reports private keys that other users can read (Linux and macOS).

## Example
`ssh_config-demo`

```
ssh_config-demo: 12 finding(s)

[CRITICAL] line 9 (Host *): SSH protocol 1 is enabled
    Protocol 1,2
    Protocol 1 is badly broken and removed from modern OpenSSH.

[HIGH] line 3 (Host *): agent forwarding is on (applies to every host)
    ForwardAgent yes
    A compromised server can use your keys while you are connected. Enable it only for hosts you fully trust, or use ProxyJump instead.

[HIGH] line 4 (Host *): host key checking is turned off
    StrictHostKeyChecking no
    Anyone on the network path can impersonate the server (applies to every host). Use 'accept-new' or leave the default.

[HIGH] line 5 (Host *): known hosts are thrown away
    UserKnownHostsFile /dev/null
    Pointing UserKnownHostsFile at /dev/null forgets every server key, so changed keys are never noticed.

[HIGH] line 6 (Host *): weak algorithm 3des-cbc in ciphers
    Ciphers aes256-ctr,3des-cbc,arcfour
    3DES is old and breakable with enough traffic. Remove it from the list.

[HIGH] line 6 (Host *): weak algorithm arcfour in ciphers
    Ciphers aes256-ctr,3des-cbc,arcfour
    RC4 (arcfour) is broken. Remove it from the list.

[HIGH] line 7 (Host *): weak algorithm hmac-md5 in macs
    MACs hmac-sha2-256,hmac-md5
    MD5-based MACs are weak. Remove it from the list.

[HIGH] line 8 (Host *): weak algorithm ssh-rsa in hostkeyalgorithms
    HostKeyAlgorithms +ssh-rsa
    ssh-rsa signatures use SHA-1; use rsa-sha2-256/512 or ed25519. Remove it from the list.

[MEDIUM] line 20 (Host build-server): X11 forwarding is on (only in Host build-server)
    ForwardX11 yes
    A remote program can watch your keystrokes and screen. Turn it off unless you need it.

[LOW] line 19 (Host build-server): password login is allowed (only in Host build-server)
    PasswordAuthentication yes
    Passwords can be guessed or phished; prefer keys (PasswordAuthentication no).

[LOW] line 21 (Host build-server): compression is on (only in Host build-server)
    Compression yes
    Compression adds little on fast links and has had security issues; leave it off unless the link is slow.

[LOW] line 22 (Host build-server): known_hosts names are stored in plain text
    HashKnownHosts no
    HashKnownHosts yes hides which servers you visit if the file leaks.
```

## Notes
- It only reads files. It never changes your SSH settings.
- `Match` blocks are labelled in the output but their conditions aren't evaluated.
- "Nothing risky found" means these checks passed, not that the setup is secure. Keep OpenSSH
  updated, and see `ssh-key-auditor` for your keys.
