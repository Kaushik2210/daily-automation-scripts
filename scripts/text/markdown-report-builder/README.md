# markdown-report-builder

## Purpose
Combine a folder of section files into one markdown report, with a title, byline and optional
table of contents. Keep each section in its own file and rebuild the report whenever one changes.

## Install
No dependencies beyond Python 3.11+.

## Usage
```
python markdown_report_builder.py sections/ --toc
python markdown_report_builder.py sections/ --title "Q4 review" --author "Ada" --output q4.md
python markdown_report_builder.py intro.md results.md --exclude "draft*"
```

- A folder contributes its `.md` files in natural order (`2-a.md` before `10-b.md`).
- A leading front matter block (`---` / `title:` / `author:` / `---`) supplies the title and author.
  The first file to set a key wins; `--title` and `--author` override it.
- `--toc` lists headings up to `--toc-depth` with working anchors. Headings in code blocks are
  ignored.
- `--output` writes a new file and refuses to overwrite one unless you add `--force`.

## Example
`report-sections/ --exclude "draft*" --toc --date 2026-11-23`

```
# Weekly engineering report

*Platform team | 2026-11-23*

## Contents

- [Summary](#summary)
- [Results](#results)
- [Risks](#risks)

# Summary

The week was mostly about search performance. Two releases shipped and the open bug count fell from 14 to 9.

# Results

| Metric | Last week | This week |
|---|---|---|
| Releases | 1 | 2 |
| Open bugs | 14 | 9 |
| P95 latency | 410 ms | 280 ms |

# Risks

- The cache migration needs a freeze window.
- One reviewer is away next week.
```

## Notes
- Sections are joined with one blank line; heading levels are left as written.
- The date line defaults to today.
