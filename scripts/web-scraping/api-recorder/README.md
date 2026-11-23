# api-recorder

## Purpose
Capture real API responses once and reuse them in tests, demos or offline development. You list the calls in a small spec file; the tool makes each request and saves a JSON **fixture** with the request, the status, the response time, the headers and the body (parsed as JSON when it is JSON). Secrets are protected: tokens are read from environment variables (`${API_TOKEN}`), and `Authorization`, cookies and API-key headers are replaced with `<redacted>` in the saved files.

## Install
Standard library only, Python 3.11+ (JSON specs). Reading a YAML spec needs PyYAML: `pip install pyyaml`.

## Usage
```bash
python api_recorder.py api-calls.json [-o fixtures] [--only NAME] [--refresh] [--apply]
python api_recorder.py --list [-o fixtures]
```
A spec looks like this:
```json
{"base_url": "https://api.example.com/v1",
 "headers": {"Authorization": "Bearer ${API_TOKEN}"},
 "calls": [{"name": "list-users", "path": "/users?limit=2"},
           {"name": "create-user", "method": "POST", "path": "/users", "body": {"name": "Test"}},
           {"name": "health", "url": "https://status.example.com/health"}]}
```
**Dry run by default:** it prints each call and whether its fixture is new or already exists, and makes no requests. With `--apply` it calls the API and writes one `NAME.json` per call into the output folder. Existing fixtures are kept unless you add `--refresh`. If a `${VARIABLE}` isn't set, `--apply` stops and names it. `--list` summarises the fixtures already recorded. Only record APIs you are allowed to call, and remember that fixtures contain response data.

## Example
```bash
python api_recorder.py api-calls.json
```
```
list-users           GET    https://api.example.com/v1/users?limit=2  [exists, kept]
get-user-1           GET    https://api.example.com/v1/users/1  [new]
create-user          POST   https://api.example.com/v1/users  [new]
health               GET    https://status.example.com/health  [new]

Note: variables not set here: API_TOKEN (needed with --apply).

Plan only: 3 call(s) would be recorded into fixtures. Use --apply to do it.
```

## Notes
- Response headers such as `Set-Cookie` are redacted too, but review a fixture before committing it: the body may contain personal data.
- Non-JSON responses are stored as text.
- Use `mock-server` to serve recorded responses and `api-smoke-tester` to check a live API.
- The website demo shows the plan and keeps recorded fixtures untouched; recording works on your own computer.
