import http.client
import json
import textwrap
import threading

import pytest
from dashboard import build_argv, discover, get_schema, make_server, run_script

DEMO = textwrap.dedent('''
    """Say hello."""
    import argparse
    import sys


    def main(argv=None):
        parser = argparse.ArgumentParser(description="Say hello.")
        parser.add_argument("name")
        parser.add_argument("--shout", action="store_true")
        parser.add_argument("--times", type=int, default=1)
        args = parser.parse_args(argv)
        for _ in range(args.times):
            print(args.name.upper() if args.shout else args.name)
        return 0


    if __name__ == "__main__":
        sys.exit(main())
''')


@pytest.fixture
def root(tmp_path):
    folder = tmp_path / "scripts" / "text" / "demo-tool"
    folder.mkdir(parents=True)
    (folder / "demo_tool.py").write_text(DEMO)
    (folder / "test_demo_tool.py").write_text("def test_x():\n    pass\n")
    (folder / "README.md").write_text("# demo\n\n## Purpose\nSays hello.\n")
    return tmp_path


def test_discover_ignores_tests_and_reads_summary(root):
    found = discover(root)
    assert list(found) == ["text/demo-tool"]
    assert found["text/demo-tool"]["summary"] == "Say hello."


def test_schema_lists_options(root):
    schema = get_schema(discover(root)["text/demo-tool"]["path"])
    by_dest = {a["dest"]: a for a in schema["arguments"]}
    assert by_dest["name"]["positional"] and by_dest["name"]["required"]
    assert by_dest["shout"]["kind"] == "flag"
    assert by_dest["times"]["type"] == "int"
    assert by_dest["times"]["default"] == 1


def test_build_argv(root):
    args = get_schema(discover(root)["text/demo-tool"]["path"])["arguments"]
    argv = build_argv(args, {"name": "Ada", "shout": True, "times": "2"})
    assert argv == ["--shout", "--times", "2", "--", "Ada"]
    with pytest.raises(ValueError):
        build_argv(args, {"name": "Ada", "bogus": 1})
    with pytest.raises(ValueError):
        build_argv(args, {})


def test_run_script_captures_output(root):
    path = discover(root)["text/demo-tool"]["path"]
    result = run_script(path, ["--times", "2", "Ada"])
    assert result["exit_code"] == 0
    assert result["stdout"] == "Ada\nAda\n"


def test_http_token_and_run(root):
    server = make_server(0, root)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/api/scripts")
        listing = json.loads(conn.getresponse().read())
        assert listing["scripts"][0]["id"] == "text/demo-tool"

        body = json.dumps({"script": "text/demo-tool", "values": {"name": "Ada"}})
        conn.request("POST", "/api/run", body)
        assert conn.getresponse().status == 403

        conn.request("POST", "/api/run", body, {"X-Dashboard-Token": server.token})
        reply = conn.getresponse()
        assert json.loads(reply.read())["stdout"] == "Ada\n"

        conn.request("GET", "/api/scripts", headers={"Host": "evil.example"})
        assert conn.getresponse().status == 403
    finally:
        server.shutdown()
