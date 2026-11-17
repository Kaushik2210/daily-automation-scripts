# markdown-link-checker

## Purpose
Find broken links in your documentation before your readers do. The tool reads markdown files (or whole folders of them) and checks every link and image: that the file it points to exists, that a `#section` anchor matches a real heading in the target page (using GitHub's anchor rules), that reference-style links like `[text][ref]` have a definition, and, if you ask, that web links still answer. Links inside code blocks and `inline code` are ignored.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python markdown_link_checker.py PATH [PATH ...] [--external] [--root DIR] [--timeout 8]
```
Each `PATH` is a markdown file or a folder (searched recursively). Local links are resolved relative to the file they are in; links starting with `/` are resolved from `--root`. Web links are only requested with `--external` (one HEAD request each, falling back to GET for servers that refuse HEAD). The exit code is 1 when any link is broken, so it works in CI.

## Example
```bash
python markdown_link_checker.py handbook/
```
```
handbook\index.md:4  BROKEN  roadmap.md  (file not found)
handbook\index.md:11  BROKEN  #faq  (no heading with that anchor)
handbook\index.md:13  BROKEN  images/team.jpg  (file not found)
handbook\setup.md:9  BROKEN  [oops]  (undefined reference link)

Checked 3 file(s): 4 broken link(s). Web links were not checked (use --external).
```

## Notes
- `mailto:`, `tel:` and similar links are skipped.
- Each web address is requested once per run even if it appears many times.
- Use `markdown-toc-generator` to build contents lists whose anchors this tool can then verify.
