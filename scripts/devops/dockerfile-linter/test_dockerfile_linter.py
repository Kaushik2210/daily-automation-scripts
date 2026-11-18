import dockerfile_linter as dl
import pytest

GOOD = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER app
HEALTHCHECK CMD python -c "print(1)"
CMD ["python", "main.py"]
"""
BAD = """FROM ubuntu
RUN apt-get update
RUN apt-get install curl
ADD app.py /app/
RUN cd /app && pip install flask
ENV DB_PASSWORD=hunter2
RUN curl https://example.com/install.sh | sh
EXPOSE 22
WORKDIR app
CMD ["a"]
CMD ["b"]
"""


def rules(text):
    return {(line, rule) for line, _, rule, _ in dl.lint(text)}


def test_good_dockerfile_is_clean():
    assert dl.lint(GOOD) == []


def test_bad_dockerfile_findings():
    found = rules(BAD)
    assert (1, "DL001") in found and (3, "DL004") in found and (4, "DL003") in found
    assert (5, "DL005") in found and (5, "DL006") in found and (6, "DL011") in found
    assert (7, "DL009") in found and (8, "DL010") in found and (9, "DL013") in found
    assert (11, "DL007") in found and (1, "DL002") in found and (1, "DL012") in found


def test_severities():
    by_rule = {rule: severity for _, severity, rule, _ in dl.lint(BAD)}
    assert by_rule["DL009"] == "error" and by_rule["DL011"] == "error"
    assert by_rule["DL001"] == "warn" and by_rule["DL012"] == "info"


@pytest.mark.parametrize("image,flagged", [
    ("python:3.12", False), ("python:latest", True), ("python", True), ("scratch", False),
    ("registry.local:5000/team/app", True), ("registry.local:5000/team/app:1.2", False),
    ("python@sha256:abc", False)])
def test_from_pinning(image, flagged):
    assert (any(rule == "DL001" for _, _, rule, _ in dl.lint(f"FROM {image}\nUSER x\n"))) == flagged


def test_continuations_and_comments():
    text = ("FROM alpine:3.20\n# a comment\nRUN apt-get update && \\\n"
            "    apt-get install -y curl \\\n    && rm -rf /var/lib/apt/lists/*\nUSER x\n")
    items = dl.parse(text)
    assert [kind for _, kind, _ in items] == ["FROM", "RUN", "USER"]
    assert items[1][0] == 3 and "curl" in items[1][2]
    assert not any(rule == "DL004" and sev != "info" for _, sev, rule, _ in dl.lint(text))


def test_copy_before_install_and_multistage_user():
    text = "FROM node:20\nCOPY . .\nRUN npm ci\nUSER node\n"
    assert (2, "DL014") in rules(text)
    staged = "FROM node:20 AS build\nRUN echo hi\nFROM nginx:1.27\nCOPY --from=build /a /b\n"
    assert any(rule == "DL002" and line == 3 for line, _, rule, _ in dl.lint(staged))


def test_no_from():
    assert dl.lint("RUN echo hi\n")[0][2] == "DL000"


def test_cli(tmp_path, capsys):
    good, bad = tmp_path / "Dockerfile", tmp_path / "Dockerfile.bad"
    good.write_text(GOOD)
    bad.write_text(BAD)
    assert dl.main([str(good)]) == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out
    assert dl.main([str(bad)]) == 1
    assert "Dockerfile.bad:6  ERROR DL011" in capsys.readouterr().out
    warn_only = tmp_path / "w"
    warn_only.write_text("FROM python\nUSER x\nHEALTHCHECK NONE\n")
    assert dl.main([str(warn_only)]) == 0
    assert dl.main([str(warn_only), "--strict"]) == 1
    assert dl.main([str(warn_only), "--strict", "--ignore", "DL001"]) == 0
    with pytest.raises(SystemExit):
        dl.main([str(tmp_path / "missing")])
