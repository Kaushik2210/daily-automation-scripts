# totp-generator

## Purpose
Generate the six-digit codes that authenticator apps show (time-based one-time passwords, RFC 6238)
from a base32 secret, and check a code someone gives you. Useful for testing a login flow, for
scripts that need a code, or for understanding how two-factor codes work.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python totp_generator.py --secret-file totp-secret.txt
python totp_generator.py --secret-file totp-secret.txt --count 3        # this code and the next two
python totp_generator.py --uri "otpauth://totp/Example:ada?secret=JBSWY3DPEHPK3PXP&issuer=Example"
python totp_generator.py --secret-file totp-secret.txt --verify 123456  # exit 0 if valid
python totp_generator.py --secret-file totp-secret.txt --format json
```

- The secret can come from `--secret-file` (first line), the `TOTP_SECRET` environment variable,
  an `otpauth://` address with `--uri`, or `--secret`. The last one works but leaves the secret in
  your shell history, so the tool warns you.
- Spaces, dashes and lower case in the secret are fine (`jbsw y3dp ehpk 3pxp`).
- `--digits` (6, 7 or 8), `--period` (30 seconds) and `--algorithm` (SHA1, SHA256 or SHA512)
  match what most services use by default; an `otpauth://` address sets them for you.
- `--verify CODE` accepts the current code and one step either side (`--window 1`), which allows
  for clocks that differ a little.
- `--time` lets you compute a code for any moment, as a unix time or an ISO date-time.

## Example
`--secret-file demo-totp-secret.txt --time 1700000000 --count 3`

```
324 550   (valid for 10 more second(s))
367 665   (in 10 s)
870 960   (in 40 s)
```

## Notes
- The code is checked against the test vectors published in RFC 4226 and RFC 6238.
- Treat a TOTP secret like a password: anyone who has it can generate your codes. The secret in
  the demo file is a well-known example and protects nothing.
- Your computer's clock must be accurate for codes to be accepted by a real service.
