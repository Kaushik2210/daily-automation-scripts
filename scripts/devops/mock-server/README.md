# mock-server

## Purpose
Pretend to be an API while you build something that depends on it. Describe the endpoints in a JSON file (method, path, status, headers, body, optional delay) and the tool serves them on a local port, with CORS headers so browser apps can call it. Paths can have parameters (`/users/{id}`), and `{id}` or `{query.name}` placeholders inside the response body or headers are filled in from the request. Unknown requests get a 404 that lists the routes you did define, which makes typos easy to spot.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python mock_server.py serve mock-api.json [--port 8080] [--host 127.0.0.1] [--no-cors] [--max-requests N]
python mock_server.py check mock-api.json
python mock_server.py simulate mock-api.json "GET /users/7?verbose=1"
```
```json
{"port": 8080,
 "routes": [
   {"method": "GET", "path": "/users/{id}", "body": {"id": "{id}", "name": "User {id}"}},
   {"method": "POST", "path": "/users", "status": 201, "headers": {"Location": "/users/3"}, "body": {"created": true}},
   {"method": "GET", "path": "/slow", "delay_ms": 1500, "body": {"ok": true}}]}
```
`method` can be `"*"` for any method; the first matching route wins. Object and list bodies are sent as JSON, strings as plain text. `check` validates the file and lists the routes; `simulate` shows the response a request would get without starting a server (handy for testing templates). The server listens on `127.0.0.1` (your computer only) unless you pass `--host`, and prints one line per request.

## Example
```bash
python mock_server.py simulate mock-api.json "GET /users/7?verbose=1"
```
```
HTTP 200
Content-Type: application/json

{"id": "7", "name": "User 7"}
```

## Notes
- Use `api-recorder` to capture real responses and paste them into the routes.
- A route with `delay_ms` makes timeouts and loading states easy to test.
- The website demo uses `simulate`; running the server works on your own computer.
