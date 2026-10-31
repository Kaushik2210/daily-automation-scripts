# python-env-reporter

## Purpose
See exactly which Python packages and versions are installed in the interpreter that runs the script. Handy when debugging "works on my machine" problems or when you want a quick requirements list.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python python_env_reporter.py [SEARCH] [--format table|json|requirements]
```
Run it with the interpreter you care about, for example from inside a virtual environment.

## Example
```bash
python python_env_reporter.py py --format requirements
```
```
pytest==9.1.1
python-dateutil==2.9.0
```

## Notes
- `SEARCH` matches part of a package name, ignoring case.
- `requirements` output can be saved straight to a `requirements.txt`.
- Read-only. It lists what is installed and does not check for newer versions.
