import json
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import bulk_repo_cloner as brc
import pytest

API_REPOS = [
    {"name": "api", "full_name": "me/api", "clone_url": "https://github.com/me/api.git",
     "ssh_url": "git@github.com:me/api.git", "language": "Python", "fork": False,
     "archived": False},
    {"name": "web", "full_name": "me/web", "html_url": "https://github.com/me/web",
     "language": "TypeScript", "fork": False, "archived": False},
    {"name": "forked", "full_name": "me/forked", "language": "Go", "fork": True,
     "archived": False},
    {"name": "old", "full_name": "me/old", "language": "Python", "fork": False, "archived": True},
    {"name": "api-tools", "full_name": "me/api-tools", "language": "Python", "fork": False,
     "archived": False}]


def test_repo_from_api_uses_clone_url_or_builds_one():
    assert brc.repo_from_api(API_REPOS[0], False)["url"] == "https://github.com/me/api.git"
    assert brc.repo_from_api(API_REPOS[0], True)["url"] == "git@github.com:me/api.git"
    assert brc.repo_from_api(API_REPOS[1], False)["url"] == "https://github.com/me/web.git"
    assert brc.repo_from_api(API_REPOS[2], True)["url"] == "git@github.com:me/forked.git"


@pytest.mark.parametrize("line,name,url", [
    ("owner/repo", "repo", "https://github.com/owner/repo.git"),
    ("https://example.com/team/tool.git", "tool", "https://example.com/team/tool.git"),
    ("git@host:team/lib.git", "lib", "git@host:team/lib.git"),
    ("owner/repo custom-name", "custom-name", "https://github.com/owner/repo.git")])
def test_repo_from_line(line, name, url):
    repo = brc.repo_from_line(line)
    assert (repo["name"], repo["url"]) == (name, url)


def test_read_list_ignores_comments_and_blanks(tmp_path):
    path = tmp_path / "r.txt"
    path.write_text("# my repos\n\nme/api\n  me/web  \n")
    assert [r["name"] for r in brc.read_list(path)] == ["api", "web"]


def test_select_filters():
    repos = [brc.repo_from_api(item, False) for item in API_REPOS]
    names = lambda chosen: [r["name"] for r in chosen]  # noqa: E731
    assert names(brc.select(repos, False, False, None, None, 0)) == ["api", "web", "api-tools"]
    assert names(brc.select(repos, True, True, None, None, 0)) == [
        "api", "web", "forked", "old", "api-tools"]
    assert names(brc.select(repos, False, False, "python", None, 0)) == ["api", "api-tools"]
    assert names(brc.select(repos, False, False, None, "api*", 0)) == ["api", "api-tools"]
    assert names(brc.select(repos, False, False, None, None, 1)) == ["api"]


def test_plan_from_saved_json(tmp_path, capsys):
    saved = tmp_path / "repos.json"
    saved.write_text(json.dumps(API_REPOS))
    dest = tmp_path / "out"
    (dest / "api").mkdir(parents=True)
    assert brc.main(["--from-json", str(saved), "--dest", str(dest)]) == 0
    out = capsys.readouterr().out
    assert "3 repositories -> " in out and "exists, skipped" in out and "will clone" in out
    assert "forked" not in out and "Dry run: 2 action(s)" in out
    assert not (dest / "web").exists()
    assert brc.main(["--from-json", str(saved), "--language", "rust"]) == 1
    with pytest.raises(SystemExit):
        brc.main(["--from-json", str(saved), "--jobs", "0"])


def test_bad_inputs(tmp_path, capsys):
    broken = tmp_path / "b.json"
    broken.write_text("{nope")
    assert brc.main(["--from-json", str(broken)]) == 1
    assert "Can't get the repository list" in capsys.readouterr().err
    assert brc.main(["--list", str(tmp_path / "missing.txt")]) == 1


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if "page=2" in self.path:
            body, link = [API_REPOS[3]], ""
        else:
            body = API_REPOS[:2]
            port = self.server.server_address[1]
            link = f'<http://127.0.0.1:{port}/users/me/repos?page=2>; rel="next"'
        self.send_response(200)
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())


def test_user_listing_follows_pages(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(brc, "API", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        assert [i["name"] for i in brc.api_repos("user", "me", 0)] == ["api", "web", "old"]
        assert len(brc.api_repos("user", "me", 1)) == 2  # stops once the limit is reached
    finally:
        server.shutdown()


@pytest.mark.skipif(not shutil.which("git"), reason="git is not installed")
def test_real_clone_and_update(tmp_path, capsys, monkeypatch):
    for key, value in (("NAME", "T"), ("EMAIL", "t@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{key}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{key}", value)
    origin = tmp_path / "origin"
    origin.mkdir()
    for args in (["init", "-q", "-b", "main"],):
        subprocess.run(["git", "-C", str(origin), *args], check=True)
    (origin / "a.txt").write_text("1")
    subprocess.run(["git", "-C", str(origin), "add", "."], check=True)
    subprocess.run(["git", "-C", str(origin), "commit", "-q", "-m", "one"], check=True)
    listing = tmp_path / "list.txt"
    listing.write_text(f"{origin.as_posix()} first\n{tmp_path.as_posix()}/does-not-exist broken\n")
    dest = tmp_path / "clones"
    assert brc.main(["--list", str(listing), "--dest", str(dest), "--apply"]) == 1
    out = capsys.readouterr().out
    assert "done  clone first" in out and "FAIL  clone broken" in out
    assert (dest / "first" / "a.txt").read_text() == "1"
    (origin / "b.txt").write_text("2")
    subprocess.run(["git", "-C", str(origin), "add", "."], check=True)
    subprocess.run(["git", "-C", str(origin), "commit", "-q", "-m", "two"], check=True)
    assert brc.main(["--list", str(listing), "--dest", str(dest), "--apply", "--update"]) == 1
    assert "done  pull  first" in capsys.readouterr().out
    assert (dest / "first" / "b.txt").exists()
