# makefile-target-lister

## Purpose
Turn a Makefile into a readable help screen. The tool lists every target with its description and its dependencies, grouped under section headings, so newcomers can see what `make test` or `make deploy` do without reading the recipes. Descriptions come from a `## text` comment on the target line, or from the comment line directly above it. Variables, pattern rules (`%.o: %.c`) and special targets like `.PHONY` are ignored.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python makefile_target_lister.py [Makefile] [--all]
```
Write documentation like this in your Makefile:
```make
##@ Development
test: ## Run the tests
	pytest
```
`##@ Name` starts a new section. By default only documented targets are shown; `--all` also lists the rest as "(no description)". Targets that are not declared in `.PHONY` are marked `[file target]` since they normally produce a file. The exit code is 1 if nothing documented was found.

## Example
```bash
python makefile_target_lister.py Makefile --all
```
```
{{OUTPUT}}
```

## Notes
- Works with any `make` (GNU, BSD, Windows `nmake`-style files are not supported).
- Multiple targets on one line (`a b: ## doc`) share the description.
- Use `markdown-toc-generator` for the same kind of help for documentation files.
