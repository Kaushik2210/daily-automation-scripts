# release-tagger

## Purpose
Decide the next version number from what changed, and tag it. The tool finds the latest version tag, reads the commit messages since then and applies the Conventional Commits rules of semantic versioning: a `feat:` means a minor release, `fix:` or `perf:` a patch release, and anything with `!` (like `feat!:`) or a `BREAKING CHANGE:` line a major release. Other commits (docs, chore, refactor...) don't need a release on their own. It prints the changes grouped by kind and the next version, and can create the annotated tag for you.

## Install
Needs `git` on your PATH for repositories. No Python packages are required.

## Usage
```bash
python release_tagger.py [--repo DIR] [--apply]
python release_tagger.py --log-file commits.txt --current v1.4.2
```
Dry run by default. With `--apply` the tool creates an annotated tag such as `v1.5.0` in the repository (listing the changes in its message) but never pushes it; it prints the `git push origin v1.5.0` command to run yourself and refuses to touch a tag that already exists. A repository with no tags starts from `v0.0.0`. For a saved list of commit subjects (`git log --format=%s > commits.txt`) pass `--log-file` and `--current`; `--apply` only works on a real repository.

## Example
```bash
python release_tagger.py --log-file commits.txt --current v1.4.2
```
```
Current version: v1.4.2   (8 commit(s) since)

Breaking changes:
  - feat!: remove the deprecated v1 endpoints

Features:
  - feat(api): add pagination to the list endpoint

Fixes:
  - fix: handle empty responses from the billing service
  - fix(ui): correct the dark mode contrast on buttons

Other (no release on their own):
  - docs: explain the retry settings
  - chore: bump dependencies
  - refactor: split the settings module
  - Update README wording

Next version: v2.0.0  (major bump)
Dry run. Use --apply to create the tag in the repository.
```

## Notes
- Commit messages that don't follow the convention count as "other", so they never cause a release.
- Pre-release suffixes (`-rc.1`) aren't handled; the tool works with plain `MAJOR.MINOR.PATCH` tags.
- Use `commit-message-linter` to keep your commit messages in the right format.
