# jwt-decoder

## Purpose
Read a JSON Web Token: show its header and claims, turn the `iat`, `nbf` and `exp` timestamps into
dates, say whether it has expired, and point out risky settings such as `alg: none`. It is for
debugging a login problem or inspecting a token, not for trusting one.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python jwt_decoder.py eyJhbGciOiJIUzI1NiIs...
python jwt_decoder.py --file token.txt
echo $TOKEN | python jwt_decoder.py                  # a leading "Bearer " is fine
python jwt_decoder.py --file token.txt --format json
JWT_SECRET=demo-secret python jwt_decoder.py --file token.txt --secret-env JWT_SECRET
python jwt_decoder.py --file token.txt --now 2026-01-01T00:00:00
```

- **Decoding is not verifying.** The first line of the output says so on purpose: anyone can write
  a token that decodes cleanly. Only a server that checks the signature with the right key can
  trust one.
- With `--secret-env NAME` it can check an HS256, HS384 or HS512 signature against a secret from
  the environment. Other algorithms (RS256, ES256 and so on) need a public key, which this tool
  doesn't handle, and are reported as "can't be checked here".
- The warnings cover `alg: none`, a missing `exp`, an expiry more than a year away, no `iss` or
  `aud`, and headers that name their own key (`jku`, `x5u`, `jwk`, `kid`).
- `--now` shows how the token looks at another moment; the default is the current time.
- Pasting a real token into an online decoder shares it with that site. Decoding it here keeps it
  on your computer.

## Example
`--file sample-jwt.txt --now 1764000000`

```
NOT VERIFIED: this only reads the token; anyone can forge one that decodes alike.

Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Claims:
{
  "sub": "1234567890",
  "name": "Ada Lovelace",
  "admin": false,
  "iss": "https://auth.example.com",
  "aud": "demo-app",
  "iat": 1763971200,
  "nbf": 1763971200,
  "exp": 1764057600
}

Times:
  iat  issued at         2025-11-24 08:00:00 UTC  (8h 0m ago)
  nbf  not valid before  2025-11-24 08:00:00 UTC  (8h 0m ago)
  exp  expires           2025-11-25 08:00:00 UTC  (in 16h 0m)

Status: within its validity window
Signature part: 32 byte(s)

Worth knowing:
  - HS256 uses a shared secret, so it can only be checked by someone who has it
```

## Notes
- Tokens often carry personal data (names, emails). Don't paste decoded output where others can see
  it.
- Times are shown in UTC.
- The sample token is signed with the made-up secret `demo-secret`.
