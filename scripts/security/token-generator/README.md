# token-generator

## Purpose
Make random tokens for API keys, session secrets, invite codes, one-time PINs or unique IDs. All randomness comes from Python's `secrets` module, which is meant for security use.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python token_generator.py [--kind urlsafe|hex|base32|numeric|uuid] [-b BYTES] [-p PREFIX] [-n COUNT]
```
`--bytes` sets how much randomness goes in (32 bytes is 256 bits). For `numeric` it is the number of digits.

## Example
```bash
python token_generator.py --kind hex -b 16 -p sk_ -n 2
```
```
sk_9c1e4f0b7a3d28e5b6f1a0c4d7e92b83
sk_41d8a6e0c9f3b27d5e8a1c4f60b93d27
```

## Notes
- A prefix such as `sk_` or `pk_` makes keys easy to recognise and easy to find with `secret-scanner`.
- Numeric PINs are short by nature; use them only where attempts are rate-limited.
- Tokens are printed and not stored. Save them in a password manager or environment variable straight away.
