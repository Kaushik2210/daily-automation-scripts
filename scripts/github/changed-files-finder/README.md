# changed-files-finder

## Purpose
In a monorepo, answer the question every CI pipeline asks: **what changed, and which projects does it affect?** The tool compares your branch with a ref (default `origin/main`, using the merge base like a pull request does), lists the added, modified, deleted and renamed files, and groups them by project folder (`apps/web`, `libs/shared`...). It can also add the projects that *depend* on a changed library, and print the result as plain text, JSON, one path per line or just the project names, ready to feed a build matrix.

## Install
Standard library only, Python 3.11+. Needs `git` on your PATH (unless you use `--from-file`).

## Usage
```bash
python changed_files_finder.py [--ref origin/main] [--projects 'apps/*' 'libs/*'] [--depends libs/shared=apps/web,apps/api]
                               [--ext py,ts] [--exclude 'docs/*'] [--include-uncommitted]
                               [--format text|json|paths|projects]
python changed_files_finder.py --from-file diff.txt --projects 'apps/*'
```
`--projects` takes folder patterns: `apps/*` makes every direct subfolder of `apps` a project. Files in no project are grouped under their top-level folder, and files in the repository root under `(root)`. `--depends LIB=USER,USER` (repeatable) lists the projects to rebuild when `LIB` changes. `--from-file` reads saved `git diff --name-status` output, which is handy when the checkout isn't available. `--include-uncommitted` also counts working-tree changes and new files. Renames count for both the old and the new project.

## Example
```bash
python changed_files_finder.py --from-file diff-names.txt --projects 'apps/*' 'libs/*' 'services/*' --depends libs/shared=apps/web,apps/mobile
```
```
10 changed file(s) in saved diff diff-names.txt

(root)  (1)
  modified     README.md
.github  (1)
  added        .github/workflows/ci.yml
apps/api  (2)
  added        apps/api/handlers/users.py
  deleted      apps/api/handlers/legacy.py
apps/web  (2)
  modified     apps/web/src/app.tsx
  modified     apps/web/package.json
docs  (1)
  modified     docs/guide.md
libs/shared  (1)
  renamed      libs/shared/new_name.py (from libs/shared/old_name.py)
libs/ui  (1)
  modified     libs/ui/button.tsx
services/billing  (1)
  modified     services/billing/main.go

Also affected through dependencies:
  apps/mobile  (depends on libs/shared)

2 added, 1 deleted, 6 modified, 1 renamed.
```

## Notes
- The three-dot comparison (`ref...HEAD`) shows only what *your* branch changed, not what the main branch gained since you branched.
- In CI, make sure the base ref is fetched (for example `fetch-depth: 0` on GitHub Actions).
- Use `git-log-summarizer` and `changelog-generator` to describe the changes in words.
