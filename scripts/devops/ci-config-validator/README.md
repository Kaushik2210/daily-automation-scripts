# ci-config-validator

## Purpose
Catch mistakes in your GitHub Actions workflow files before pushing them and waiting for a failed run. The validator parses each workflow and checks that it has `on` and `jobs`, that every job has `runs-on` and `steps`, that `needs` points to real jobs, that every step has `uses` or `run` (not both) and no duplicate `id`. It also warns about actions without a version or pinned to a moving branch like `@main`, outdated actions such as `checkout@v2`, untrusted text like a pull-request title used directly inside `run:` (a command-injection risk), and missing `permissions` or `timeout-minutes`.

## Install
Needs PyYAML:
```bash
pip install -r requirements.txt
```

## Usage
```bash
python ci_config_validator.py PATH [PATH ...] [--strict]
```
Give workflow files or a folder such as `.github/workflows` (searched recursively for `.yml` and `.yaml`). Findings are listed per file as ERROR, WARN or INFO with their location (for example `jobs.test.steps[3]`). The exit code is 1 on any ERROR, or on warnings too with `--strict`.

## Example
```bash
python ci_config_validator.py workflows/
```
```
workflows\ci.yml: 10 finding(s)
  ERROR jobs.test.steps[5] (Bad step): a step can have 'uses' or 'run', not both
  ERROR jobs.deploy: missing 'runs-on'
  ERROR jobs.deploy: needs 'build', but there is no such job
  ERROR jobs.deploy.steps[2]: duplicate step id 'ship' (also steps[1])
  WARN  jobs.test.steps[1]: actions/checkout@v2 is old; the current major is v4
  WARN  jobs.test.steps[2]: 'actions/setup-python@main' follows a moving branch; pin a tag or commit sha
  WARN  jobs.test.steps[4] (Greet the author): untrusted text (PR title, branch, comment...) in 'run' can inject commands; pass it through env
  INFO  file: no 'permissions': the token gets the repository default
  INFO  jobs.test: no 'timeout-minutes' (a stuck job runs up to 6 hours)
  INFO  jobs.deploy: no 'timeout-minutes' (a stuck job runs up to 6 hours)
workflows\release.yml: OK

2 file(s): 4 error(s), 3 warning(s), 3 suggestion(s).
```

## Notes
- This checks structure and common risks; it does not run the workflow or know every action's inputs.
- The list of "current" action versions is small and built in; update it in the script when new majors appear.
- Use `dockerfile-linter` for the Dockerfiles your workflows build.
