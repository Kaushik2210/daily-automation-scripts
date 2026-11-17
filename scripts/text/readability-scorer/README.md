# readability-scorer

## Purpose
Find out how hard your writing is to read. The tool counts sentences, words and syllables and computes five well-known scores: Flesch reading ease (higher is easier; 60-70 is plain English), and the Flesch-Kincaid, Gunning fog, Coleman-Liau, SMOG and ARI grade levels (the US school grade needed to understand the text), plus their average. Use it to keep documentation, emails or web copy at the level your audience expects.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python readability_scorer.py FILE [FILE ...] [--target-grade 9]
```
`--target-grade` makes the exit code 1 when a file's average grade is above the target, so it can check writing in CI. Syllables are estimated with rules for English, so scores are approximate, and very short texts (under a few sentences) are unreliable.

## Example
```bash
python readability_scorer.py plain-english.txt article-long.txt
```
```
{{OUTPUT}}
```

## Notes
- Scores favour short sentences and short words; a low grade doesn't guarantee a clear text.
- Headings and bullet points without full stops count as sentence breaks only at blank lines.
- Use `word-counter` for basic counts and `text-summarizer` for the main points.
