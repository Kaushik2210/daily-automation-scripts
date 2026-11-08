# meta-tag-auditor

## Purpose
Check the small things search engines and social networks read before they show your page. The tool audits the title and description length, canonical link, viewport, language, heading structure, `noindex` flags and the Open Graph and Twitter card tags, then lists what's fine and what needs fixing.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python meta_tag_auditor.py SOURCE [SOURCE ...] [--problems-only] [--strict]
```
Each `SOURCE` is a URL or a saved `.html` file. A missing title or description counts as a failure and makes the exit code 1; other issues are warnings (exit 0) unless you add `--strict`. Use `--problems-only` for a short to-do list.

## Example
```bash
python meta_tag_auditor.py seo-page.html --problems-only
```
```
seo-page.html: 1/12 checks passed
  [WARN] title: only 4 characters (aim for 30-60)
  [FAIL] meta description: missing
  [WARN] canonical link: missing
  [WARN] viewport: missing (not mobile friendly)
  [WARN] html lang: missing
  [WARN] h1: found 2, expected exactly one
  [WARN] robots: page tells search engines not to index it
  [WARN] og:description: missing
  [WARN] og:image: missing
  [WARN] og:url: missing
  [WARN] twitter:card: missing
```

## Notes
- Recommended lengths are 30-60 characters for the title and 70-160 for the description. They are rules of thumb, not hard limits.
- Only the first `<meta>` tag with a given name is used, as most crawlers do.
- The audit reads the HTML the server sends. Tags added later by JavaScript are not seen.
- On the website demo only saved files can be audited; URLs work on your own computer.
