# api-smoke-tester

## Purpose
Answer "is my API alive and behaving?" in a few seconds, from a plain JSON file. Each test names an endpoint and what you expect: the status code, fields in the JSON response (nested paths like `data.user.id`), text in the body, a response header, and a maximum response time. The tool runs the tests in order and prints PASS or FAIL with the reason, which makes it a good post-deploy check or CI step.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python api_smoke_tester.py smoke-tests.json [--base-url https://staging.example.com] [--only NAME] [--fail-fast] [--timeout 10]
python api_smoke_tester.py smoke-tests.json --validate
```
```json
{"base_url": "https://api.example.com",
 "headers": {"Authorization": "Bearer ${API_TOKEN}"},
 "tests": [
   {"name": "health", "path": "/health", "expect_status": 200, "max_ms": 500},
   {"name": "user 1", "path": "/users/1", "expect_json": {"name": "Ada", "tags.0": "*"}},
   {"name": "create", "method": "POST", "path": "/users", "body": {"name": "Zed"},
    "expect_status": 201, "expect_contains": "Zed"}]}
```
`expect_status` defaults to 200. In `expect_json` a value of `"*"` means "the field must exist". `expect_header` checks that a header contains some text (case-insensitively). Header values can use `${ENV_VARS}`, so tokens stay out of the file. `--validate` checks the file and lists the tests without making any request. The exit code is 1 if any test fails. Only test APIs you own or are allowed to test.

## Example
```bash
python api_smoke_tester.py smoke-tests.json --validate
```
```
ok  GET    health                 https://api.example.com/health  [status, max_ms]
ok  GET    users list             https://api.example.com/users  [status, json, header]
ok  GET    user 1                 https://api.example.com/users/1  [json]
ok  GET    missing user           https://api.example.com/users/999  [status]
ok  POST   create                 https://api.example.com/users  [status, contains]

5 test(s) look valid. No requests were made.
```

## Notes
- Mistakes in the file (unknown settings, duplicate names, a missing URL) are reported before anything runs.
- A test that can't reach the server fails with the reason, rather than stopping the whole run.
- Use `latency-benchmark` for response-time statistics and `health-check-poller` for repeated checks.
- The website demo validates the test file; running the tests works on your own computer.
