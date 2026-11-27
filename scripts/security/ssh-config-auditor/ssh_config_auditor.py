"""Review an ssh_config (or sshd_config) for risky settings and explain how to fix each one."""
import argparse
import fnmatch
import json
import os
import re
import stat
import sys
from pathlib import Path

LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
WEAK_ALGORITHMS = {
    "3des-cbc": ("high", "3DES is old and breakable with enough traffic"),
    "arcfour*": ("high", "RC4 (arcfour) is broken"),
    "blowfish-cbc": ("high", "Blowfish in CBC mode is obsolete"),
    "cast128-cbc": ("high", "CAST-128 in CBC mode is obsolete"),
    "aes128-cbc": ("medium", "CBC ciphers have known weaknesses; prefer CTR or GCM"),
    "aes192-cbc": ("medium", "CBC ciphers have known weaknesses; prefer CTR or GCM"),
    "aes256-cbc": ("medium", "CBC ciphers have known weaknesses; prefer CTR or GCM"),
    "hmac-md5*": ("high", "MD5-based MACs are weak"),
    "hmac-sha1*": ("medium", "SHA-1 MACs are aging; prefer SHA-2 or ETM variants"),
    "umac-64*": ("medium", "a 64-bit MAC is short"),
    "diffie-hellman-group1-sha1": ("critical", "1024-bit Diffie-Hellman with SHA-1 can be broken"),
    "diffie-hellman-group14-sha1": ("medium", "SHA-1 key exchange is aging"),
    "diffie-hellman-group-exchange-sha1": ("medium", "SHA-1 key exchange is aging"),
    "ssh-rsa": ("high", "ssh-rsa signatures use SHA-1; use rsa-sha2-256/512 or ed25519"),
    "ssh-dss": ("critical", "DSA keys are obsolete and too short"),
}
ALGORITHM_KEYS = {"ciphers", "macs", "kexalgorithms", "hostkeyalgorithms",
                  "pubkeyacceptedalgorithms", "pubkeyacceptedkeytypes",
                  "hostbasedacceptedalgorithms"}
TRUE = {"yes", "true", "on"}
FALSE = {"no", "false", "off"}


def parse(text):
    """Return directives as dicts: line, context ('global', 'Host x', 'Match y'), key, value."""
    directives, context = [], "global"
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9]+)\s*(?:=\s*|\s+)(.*)$", line)
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip().strip('"')
        if key in ("host", "match"):
            context = f"{key.title()} {value}"
        directives.append({"line": number, "context": context, "key": key, "name": match.group(1),
                           "value": value,
                           "global": context == "global" or context in ("Host *", "Match all")})
    return directives


def finding(d, severity, title, advice):
    return {"line": d["line"], "context": d["context"], "setting": f"{d['name']} {d['value']}",
            "severity": severity, "title": title, "advice": advice}


def check_algorithms(d):
    found = []
    for item in re.split(r"[,\s]+", d["value"]):
        name = item.lstrip("+-^").lower()
        for pattern, (severity, why) in WEAK_ALGORITHMS.items():
            if name and fnmatch.fnmatch(name, pattern):
                if item.startswith("-"):
                    continue  # explicitly removing a weak algorithm is good
                found.append(finding(d, severity, f"weak algorithm {name} in {d['key']}",
                                     f"{why}. Remove it from the list."))
    return found


def client_checks(d, check_files, home):
    key, low = d["key"], d["value"].lower()
    wide = "applies to every host" if d["global"] else f"only in {d['context']}"
    found = []
    if key == "stricthostkeychecking" and low in FALSE:
        found.append(finding(d, "high", "host key checking is turned off",
                             f"Anyone on the network path can impersonate the server ({wide}). "
                             "Use 'accept-new' or leave the default."))
    if key == "userknownhostsfile" and low in ("/dev/null", "nul"):
        found.append(finding(d, "high", "known hosts are thrown away",
                             "Pointing UserKnownHostsFile at /dev/null forgets every server key, "
                             "so changed keys are never noticed."))
    if key == "forwardagent" and low in TRUE:
        found.append(finding(d, "high" if d["global"] else "medium",
                             f"agent forwarding is on ({wide})",
                             "A compromised server can use your keys while you are connected. "
                             "Enable it only for hosts you fully trust, or use ProxyJump instead."))
    if key == "forwardx11" and low in TRUE:
        found.append(finding(d, "medium", f"X11 forwarding is on ({wide})",
                             "A remote program can watch your keystrokes and screen. Turn it off "
                             "unless you need it."))
    if key == "forwardx11trusted" and low in TRUE:
        found.append(finding(d, "high", "trusted X11 forwarding is on",
                             "ForwardX11Trusted removes the X11 safeguards. Use -X without it."))
    if key == "passwordauthentication" and low in TRUE:
        found.append(finding(d, "medium" if d["global"] else "low",
                             f"password login is allowed ({wide})",
                             "Passwords can be guessed or phished; prefer keys "
                             "(PasswordAuthentication no)."))
    if key == "protocol" and "1" in re.split(r"[,\s]+", low):
        found.append(finding(d, "critical", "SSH protocol 1 is enabled",
                             "Protocol 1 is badly broken and removed from modern OpenSSH."))
    if key == "permitlocalcommand" and low in TRUE:
        found.append(finding(d, "medium", "LocalCommand can run programs on your machine",
                             "Only enable PermitLocalCommand if you wrote the LocalCommand."))
    if key == "hashknownhosts" and low in FALSE:
        found.append(finding(d, "low", "known_hosts names are stored in plain text",
                             "HashKnownHosts yes hides which servers you visit if the file leaks."))
    if key == "compression" and low in TRUE:
        found.append(finding(d, "low", f"compression is on ({wide})",
                             "Compression adds little on fast links and has had security "
                             "issues; leave it off unless the link is slow."))
    if key == "verifyhostkeydns" and low in TRUE:
        found.append(finding(d, "low", "host keys are trusted from DNS",
                             "Only safe when DNSSEC is validated end to end."))
    if key == "identityfile" and check_files:
        found += check_key_file(d, home)
    return found


def check_key_file(d, home):
    path = Path(d["value"].replace("~", str(home), 1)) if d["value"].startswith("~") \
        else Path(d["value"])
    if "%" in d["value"] or not path.is_file():
        return []
    if os.name != "nt" and path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        return [finding(d, "high", f"private key {path.name} is readable by other users",
                        f"Run: chmod 600 {path}. OpenSSH may also refuse to use it.")]
    return []


def server_checks(d):
    key, low = d["key"], d["value"].lower()
    found = []
    if key == "permitrootlogin" and low in TRUE:
        found.append(finding(d, "high", "root can log in over SSH",
                             "Use PermitRootLogin prohibit-password (or no) and log in as a "
                             "normal user."))
    if key == "permitemptypasswords" and low in TRUE:
        found.append(finding(d, "critical", "accounts with empty passwords can log in",
                             "Set PermitEmptyPasswords no."))
    if key == "passwordauthentication" and low in TRUE:
        found.append(finding(d, "medium", "password login is allowed",
                             "Use keys and set PasswordAuthentication no."))
    if key == "pubkeyauthentication" and low in FALSE:
        found.append(finding(d, "medium", "key login is disabled",
                             "Keys are the safer option; set PubkeyAuthentication yes."))
    if key in ("hostbasedauthentication", "permituserenvironment") and low in TRUE:
        found.append(finding(d, "high", f"{key} is on",
                             f"Set {key} no unless you really need it."))
    if key in ("ignorerhosts", "strictmodes") and low in FALSE:
        found.append(finding(d, "high", f"{key} is off", f"Set {key} yes."))
    if key == "x11forwarding" and low in TRUE:
        found.append(finding(d, "low", "X11 forwarding is allowed", "Turn it off if unused."))
    if key == "protocol" and "1" in re.split(r"[,\s]+", low):
        found.append(finding(d, "critical", "SSH protocol 1 is enabled", "Use Protocol 2 only."))
    if key == "maxauthtries" and low.isdigit() and int(low) > 6:
        found.append(finding(d, "low", f"{low} login attempts per connection",
                             "Lower MaxAuthTries to 3-4 to slow down guessing."))
    if key == "logingracetime" and low.isdigit() and int(low) > 120:
        found.append(finding(d, "low", "long login grace time",
                             "A shorter LoginGraceTime frees connections held by attackers."))
    return found


def audit(text, server=False, check_files=False, home=None):
    home = home or Path.home()
    findings, includes = [], []
    for d in parse(text):
        if d["key"] == "include":
            includes.append(d["value"])
        if d["key"] in ALGORITHM_KEYS:
            findings += check_algorithms(d)
        findings += server_checks(d) if server else client_checks(d, check_files, home)
    findings.sort(key=lambda f: (-LEVELS[f["severity"]], f["line"]))
    return findings, includes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review an ssh_config for risky settings.")
    parser.add_argument("config", nargs="?", type=Path,
                        help="the file to review (default: ~/.ssh/config)")
    parser.add_argument("--server", action="store_true", help="treat it as an sshd_config")
    parser.add_argument("--check-files", action="store_true",
                        help="also check the permissions of IdentityFile key files")
    parser.add_argument("--min-severity", choices=list(LEVELS), default="low",
                        help="hide findings below this level (low)")
    parser.add_argument("--fail-on", choices=["none", "medium", "high", "critical"], default="none",
                        help="exit 1 if a finding is at least this serious (none)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    args.config = args.config or Path.home() / ".ssh" / "config"
    try:
        text = args.config.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"Can't read {args.config}: {err}", file=sys.stderr)
        return 1
    findings, includes = audit(text, args.server, args.check_files)
    findings = [f for f in findings if LEVELS[f["severity"]] >= LEVELS[args.min_severity]]
    if args.format == "json":
        print(json.dumps({"file": str(args.config), "findings": findings,
                          "includes_not_followed": includes}, indent=1))
    else:
        print(f"{args.config}: {len(findings)} finding(s)")
        for f in findings:
            print(f"\n[{f['severity'].upper()}] line {f['line']} ({f['context']}): {f['title']}")
            print(f"    {f['setting']}\n    {f['advice']}")
        if includes:
            print(f"\nNot followed: Include {', '.join(includes)}. Audit those files too.")
        if not findings:
            print("Nothing risky found. That doesn't prove the setup is secure.")
    limit = LEVELS.get(args.fail_on)
    bad = args.fail_on != "none" and any(LEVELS[f["severity"]] >= limit for f in findings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
