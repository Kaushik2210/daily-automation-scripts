# csp-builder

## Purpose
Build a Content-Security-Policy header, the browser rule that limits where a page may load scripts,
styles, images and more from, and one of the best defences against cross-site scripting. Start from
a sensible preset, add the hosts you really use, get a list of risky choices, and print the result
ready to paste into your server config.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python csp_builder.py --preset strict
python csp_builder.py --preset balanced --allow script-src=https://cdn.example.com \
    --allow connect-src=https://api.example.com --nonce --report-uri /csp-reports
python csp_builder.py --preset basic --format nginx
python csp_builder.py --preset strict --report-only          # log violations without blocking
python csp_builder.py --interactive                          # answer a few questions instead
```

Presets: `strict` (everything from your own origin only), `balanced` (own origin, plus images and
fonts over HTTPS), `basic` (a light start that still blocks plugins and framing) and `api` (for
responses that are only data).

- `--allow DIRECTIVE=source,source` adds sources (repeatable); `--remove DIRECTIVE` drops one.
  `self` and `none` are quoted for you.
- `--nonce` adds a `'nonce-{{nonce}}'` placeholder to `script-src` and `style-src`. Your server must
  replace it with a fresh random value on every response and put the same value on your inline
  `<script nonce="...">` tags.
- Formats: `header` (default), `meta`, `nginx`, `apache`, `express` and `json`. A `<meta>` tag can't
  carry `frame-ancestors`, `report-uri` or `sandbox`, and the tool says so.
- The checks print to stderr as `warning:` or `info:` lines: `'unsafe-inline'` without a nonce,
  `'unsafe-eval'`, `*`, `http:` sources, `data:` in scripts, a missing `object-src`, `base-uri` or
  `frame-ancestors`. `--strict` makes any warning exit 1, which suits a CI check.

## Example
`--preset balanced --allow script-src=https://cdn.example.com --allow connect-src=https://api.example.com --nonce --report-uri /csp-reports`

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com 'nonce-{{nonce}}'; style-src 'self' 'nonce-{{nonce}}'; img-src 'self' data: https:; font-src 'self' https: data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; upgrade-insecure-requests; connect-src https://api.example.com; report-uri /csp-reports
```

## Notes
- Roll a new policy out with `--report-only` first, watch the reports, then switch to the enforcing
  header.
- A policy can only restrict what the browser enforces; it doesn't replace validating input and
  escaping output.
- Check the result against your real site, since a policy that is too tight will break pages.
