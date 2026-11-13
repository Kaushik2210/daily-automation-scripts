# cert-chain-viewer

## Purpose
See the whole trust chain behind a website's HTTPS certificate. For each certificate - the server's own, the intermediate CA that signed it and the root - the tool prints who it was issued to and by, the validity dates with the days left, the key type and size (RSA 2048-bit, EC P-256...), the signature algorithm, serial number, SHA-256 fingerprint and the host names it covers. It also checks that every certificate was issued by the next one in the list and flags broken links and expired certificates. It needs no OpenSSL.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python cert_chain_viewer.py example.com [--timeout 8]
python cert_chain_viewer.py example.com:8443
python cert_chain_viewer.py fullchain.pem [--today 2026-11-13]
```
Give a host (optionally with a port) to connect and read what the server presents, or a `.pem`/`.crt` file such as `fullchain.pem` from your web server. On Python 3.13+ the chain is exactly what the server sent; on older versions the tool reads the server's certificate and follows its "CA Issuers" links to find the parents. The exit code is 1 if any certificate has expired, a link in the chain doesn't match, or nothing could be read.

## Example
```bash
python cert_chain_viewer.py fullchain.pem --today 2026-11-13
```
```
3 certificate(s), from fullchain.pem. Signatures are not verified here.

[1] example.com  (server certificate)
    issuer     Demo Intermediate CA 1
    valid      2026-10-01 to 2027-01-01 (49 day(s) left)
    key        RSA 2048-bit, signed with sha256WithRSA
    serial     6299EDFAA36ECBCD0AEB04BAE222FF9A2087D65B
    SHA-256    FB:78:36:4B:2F:3D:69:86:F5:8E:54:85:42:99:73:58:10:46:0D:98:F5:74:37:77:AB:4C:E3:BB:A1:47:EF:F0
    names      example.com, www.example.com
    link       issued by the next certificate

[2] Demo Intermediate CA 1  (intermediate CA)
    issuer     Demo Root CA
    valid      2024-01-01 to 2030-01-01 (1145 day(s) left)
    key        RSA 3072-bit, signed with ecdsa-with-SHA256
    serial     133624FE770202EB53CCA968438578CC9C13B694
    SHA-256    EB:A5:93:7C:00:32:77:97:5B:50:84:AC:33:2E:DF:86:8E:B3:6D:D3:A2:4F:55:E5:03:F4:62:BB:20:BB:B5:B8
    link       issued by the next certificate

[3] Demo Root CA  (root CA)
    issuer     Demo Root CA
    valid      2026-11-13 to 2036-11-10 (3650 day(s) left)
    key        EC P-384, signed with ecdsa-with-SHA256
    serial     3AFC5C4915EC05372E9A7F862247588D5284227F
    SHA-256    3B:A5:09:4A:26:A7:19:3D:FD:71:7C:84:96:BD:46:5B:C2:4B:12:DA:E0:71:49:D9:78:A6:D4:3A:3A:B7:09:CA
    link       self-signed root (the end of the chain)
```

## Notes
- Signatures are not cryptographically verified and the root isn't checked against a trust store; this tool shows the chain, it doesn't vouch for it.
- A server normally leaves out the root, so "not self-signed: the chain doesn't include its root" is expected for live hosts.
- Use `ssl-expiry-checker` to monitor several certificates' expiry dates.
- The website demo reads certificate files; checking a live host works on your own computer.
