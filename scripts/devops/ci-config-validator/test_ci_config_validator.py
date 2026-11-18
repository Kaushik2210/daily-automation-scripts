import ci_config_validator as ccv
import pytest

GOOD = """name: CI
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - name: Test
        run: pytest
"""
BAD = """name: Bad
on: [push, nonsense]
mystery: 1
jobs:
  a:
    steps:
      - uses: actions/checkout@v2
      - uses: some/action
      - uses: other/action@main
      - uses: actions/cache@v4
        run: echo hi
      - name: empty
      - run: echo "${{ github.event.pull_request.title }}"
        id: x
      - run: echo done
        id: x
  b:
    needs: [a, ghost]
    runs-on: ubuntu-latest
    steps: []
"""


def messages(text):
    return [(severity, where, message) for severity, where, message in ccv.validate(text)]


def test_good_workflow_has_no_findings():
    assert ccv.validate(GOOD) == []


def test_bad_workflow_findings():
    found = messages(BAD)
    texts = " | ".join(f"{s} {w} {m}" for s, w, m in found)
    assert "unknown trigger 'nonsense'" in texts and "unknown top-level key 'mystery'" in texts
    assert "jobs.a missing 'runs-on'" in texts
    assert "actions/checkout@v2 is old; the current major is v4" in texts
    assert "'some/action' has no version" in texts and "follows a moving branch" in texts
    assert "'uses' or 'run', not both" in texts and "needs 'uses' or 'run'" in texts
    assert "can inject commands" in texts and "duplicate step id 'x'" in texts
    assert "needs 'ghost', but there is no such job" in texts and "missing 'steps'" in texts
    assert [s for s, _, _ in found] == sorted((s for s, _, _ in found),
                                              key=lambda s: ccv.SEVERITY[s])


def test_on_key_parsed_as_true_is_handled():
    assert ccv.validate("on: push\njobs:\n  a:\n    runs-on: x\n    timeout-minutes: 1\n"
                        "    steps:\n      - run: echo\npermissions: {}\n") == []
    assert ccv.validate("jobs:\n  a:\n    runs-on: x\n    steps:\n      - run: echo\n")[0][2] == (
        "missing 'on': say when the workflow should run")


def test_reusable_workflow_jobs_and_local_actions():
    text = ("on: push\npermissions: {}\njobs:\n  call:\n"
            "    uses: org/repo/.github/workflows/x.yml@v1\n"
            "  local:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n"
            "      - uses: ./.github/actions/y\n")
    assert ccv.validate(text) == []


@pytest.mark.parametrize("text,fragment", [
    ("on: [push\n", "not valid YAML"), ("- a\n- b\n", "must be a YAML mapping"),
    ("on: push\n", "missing 'jobs'")])
def test_structural_errors(text, fragment):
    assert fragment in ccv.validate(text)[0][2]


def test_cli_folder_and_exit_codes(tmp_path, capsys):
    folder = tmp_path / "wf"
    folder.mkdir()
    (folder / "good.yml").write_text(GOOD)
    assert ccv.main([str(folder)]) == 0
    assert "1 file(s): 0 error(s), 0 warning(s)" in capsys.readouterr().out
    (folder / "bad.yaml").write_text(BAD)
    assert ccv.main([str(folder)]) == 1
    out = capsys.readouterr().out
    assert "good.yml: OK" in out and "ERROR jobs.a: missing 'runs-on'" in out
    warn_only = folder / "warn.yml"
    warn_only.write_text(GOOD.replace("checkout@v4", "checkout@main"))
    assert ccv.main([str(warn_only)]) == 0
    assert ccv.main([str(warn_only), "--strict"]) == 1
    assert ccv.main([str(tmp_path / "empty")]) == 1
