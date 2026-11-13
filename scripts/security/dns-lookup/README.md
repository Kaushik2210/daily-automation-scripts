# dns-lookup

## Purpose
Check how a domain is set up, from any computer without needing `dig` or `nslookup`. The tool asks a public DNS service for a domain's records (A and AAAA addresses, MX mail servers, TXT, NS name servers, CNAME aliases, SOA and CAA) and prints them in plain language: mail servers sorted by priority, and TXT records labelled when they are SPF, DKIM, DMARC or common verification entries. DNS errors such as "this domain does not exist" are explained instead of shown as codes.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python dns_lookup.py example.com [--types A,AAAA,MX,TXT,NS] [--resolver cloudflare|google]
python dns_lookup.py example.com --types MX,TXT --from-file saved-answers.json
```
Lookups use DNS-over-HTTPS (Cloudflare by default, or Google), because the standard library can't speak DNS directly for anything but addresses. The domain you ask about is sent to that service; nothing else is. `--from-file` reads answers saved earlier in the form `{"MX": <the JSON the service returned>, ...}`. The exit code is 1 when a lookup fails or the domain doesn't exist.

## Example
```bash
python dns_lookup.py example.com --from-file dns-response.json
```
```
DNS records for example.com

A      93.184.216.34  (TTL 300s)
AAAA   2606:2800:21f:cb07:6820:80da:af6b:8b2c  (TTL 300s)
MX     priority 10  mail1.example.com  (TTL 300s)
       priority 20  mail2.example.com  (TTL 300s)
TXT    v=spf1 include:_spf.example.com ~all   [SPF: which servers may send mail for this domain]  (TTL 3600s)
       google-site-verification=abc123   [Google domain verification]  (TTL 3600s)
NS     a.iana-servers.net  (TTL 86400s)
       b.iana-servers.net  (TTL 86400s)
```

## Notes
- Answers come from a public resolver's cache, so a recent DNS change can take up to the record's TTL to show.
- Only the record types listed above are supported.
- The website demo reads saved answers; live lookups work on your own computer.
