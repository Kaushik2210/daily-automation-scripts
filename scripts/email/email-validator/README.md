# email-validator

## Purpose
Weed out bad addresses before you send. The tool checks each address for valid syntax (name part, dots, domain labels, international domains) and, unless you turn it off, asks DNS whether the domain really accepts mail by looking up its MX record. It reports every address as ok, warn or BAD with a plain-English reason.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python email_validator.py ADDRESS [ADDRESS ...] [--file addresses.txt] [--no-mx]
```
Lines starting with `#` in the `--file` are ignored. The exit code is 1 if any address is bad or can't be checked. MX lookups use Cloudflare's public DNS-over-HTTPS service (`cloudflare-dns.com`), so only the domain part of each address is sent, once per domain.

## Example
```bash
python email_validator.py --file emails.txt --no-mx
```
```
ok    alice@acme.test  (syntax only)
ok    bob.smith+news@example.com  (syntax only)
BAD   not-an-email  (missing @)
BAD   sam@@example.org  (needs exactly one @)
BAD   .dot@example.com  (dots in the wrong place in the name part)
ok    name@sub-domain.example.co.uk  (syntax only)
BAD   user@-bad-.com  (domain has invalid characters, hyphens or lengths)
BAD   trailing.dot.@example.com  (dots in the wrong place in the name part)
BAD   ünïcode@example.com  (non-ASCII characters in the name part)
3 of 9 address(es) look fine.
```

## Notes
- A valid-looking address with a mail server can still be a mailbox that doesn't exist. Only sending a message proves that.
- Addresses with non-ASCII characters before the `@` are reported as BAD because many mail systems can't deliver to them.
- A domain with no MX record but an address record is marked `warn`, since mail servers will still try delivering there.
- A "null MX" record (a domain saying it never receives mail) counts as BAD.
- The website demo checks syntax only (`--no-mx`); MX lookups work on your own computer.
