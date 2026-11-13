# whois-lookup

## Purpose
See who is behind a domain and when it runs out. The tool performs a WHOIS lookup - first asking IANA which registry manages the domain's ending (.com, .org, .uk...), then that registry, and then the registrar's own server for extra detail - and turns the answer into a tidy summary: registrar, creation, update and expiry dates (with the days remaining), status flags, name servers, DNSSEC and, where the registry still publishes it, the organisation and abuse contact. It works without the `whois` command that Windows doesn't include.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python whois_lookup.py example.com [--raw] [--no-follow] [--timeout 10]
python whois_lookup.py --from-file saved-whois.txt
```
`--raw` also prints the full WHOIS text the servers returned. `--no-follow` stops at the registry and skips the registrar's server. Lookups use the plain WHOIS protocol on TCP port 43, so a firewall that blocks that port will block the tool. Registries differ in what they publish, and since 2018 personal details are usually hidden ("redacted"), so a missing owner name is normal. The exit code is 1 when no details could be found or the lookup failed.

## Example
```bash
python whois_lookup.py --from-file whois.txt --today 2026-11-13
```
```
Domain:        EXAMPLE.COM
Registrar:     Example Registrar, Inc.
Created:       1995-08-14
Updated:       2026-08-14
Expires:       2027-08-13 (273 day(s) left)
Organisation:  Internet Assigned Numbers Authority
Country:       US
DNSSEC:        signedDelegation
Abuse contact: abuse@registrar.example
Status:        clientDeleteProhibited
               clientTransferProhibited
Name servers:  a.iana-servers.net
               b.iana-servers.net
```

## Notes
- Use `dns-lookup` for a domain's DNS records and `ssl-expiry-checker` for its certificate.
- Some registries limit how many lookups you can make; don't script thousands of them.
- The website demo reads saved WHOIS text; live lookups work on your own computer.
