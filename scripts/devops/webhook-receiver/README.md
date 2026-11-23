# webhook-receiver

## Purpose
See exactly what a service sends to your webhook URL while you develop. `serve` starts a small local server that accepts any request, answers it (200 by default), prints one line per request and appends the full details (method, path, headers, parsed body, size) to a log file. If you give it the shared secret, it checks each request's HMAC SHA-256 signature (the `X-Hub-Signature-256` style used by GitHub and many others) and marks it valid or INVALID, optionally answering 401 for bad signatures. `show` reads a log back, and `verify` checks a saved payload against a signature when you are debugging.

## Install
Standard library only, Python 3.11+. Nothing to install. To receive webhooks from the internet you also need a tunnel such as ngrok or Cloudflare Tunnel pointing at your port.

## Usage
```bash
python webhook_receiver.py serve [--port 8000] [--log webhook-log.jsonl] [--secret SHARED_SECRET]
                                 [--status 200] [--reject-invalid] [--max-requests N]
python webhook_receiver.py show webhook-log.jsonl [--path /hooks/github] [--last 20]
python webhook_receiver.py verify payload.json --secret SHARED_SECRET --signature sha256=...
```
The server listens on `127.0.0.1` (your computer only) unless you pass `--host`. `Authorization`, `Cookie` and API-key headers are replaced with `<redacted>` in the log, but bodies are stored as received, so treat the log as sensitive. `show` exits with 1 if the log contains an INVALID signature; `verify` exits with 1 when the signature doesn't match.

## Example
```bash
python webhook_receiver.py show webhook-log.jsonl
```
```
09:00:12  POST   /hooks/github      valid       61 B  {"ref": "refs/heads/main", "commits": 3}
09:03:40  POST   /hooks/stripe      none        44 B  {"type": "invoice.paid", "amount": 4900}
09:07:05  POST   /hooks/github      INVALID     38 B  {"action": "opened", "number": 42}
09:15:31  GET    /health            none         0 B  (no body)
09:21:02  POST   /hooks/form        none        32 B  name=Ada&email=ada%40example.com

5 request(s), 1 with an INVALID signature; showing the last 5.
```

## Notes
- Signatures are computed over the raw request body, which is why `verify` reads the file as bytes; re-formatting the JSON changes the signature.
- Bodies over 1 MB are cut off.
- Use `mock-server` to pretend to be an API and `api-recorder` to capture real API responses.
- The website demo shows a saved log; running the server works on your own computer.
