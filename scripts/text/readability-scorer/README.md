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
plain-english.txt: 42 words, 9 sentences (4.7 words each, 0% long words)
  Reading ease   117.5  very easy (about 5th grade)
  Flesch-Kincaid grade  0.0
  Gunning fog    grade  1.9
  Coleman-Liau   grade  0.0
  SMOG           grade  3.1
  ARI            grade  0.0
  Average grade   0.0
article-long.txt: 245 words, 18 sentences (13.6 words each, 15% long words)
  Reading ease    53.5  fairly difficult (10th-12th grade)
  Flesch-Kincaid grade  9.2
  Gunning fog    grade 11.3
  Coleman-Liau   grade 11.9
  SMOG           grade 11.2
  ARI            grade  9.3
  Average grade  10.6
```

## Notes
- Scores favour short sentences and short words; a low grade doesn't guarantee a clear text.
- Headings and bullet points without full stops count as sentence breaks only at blank lines.
- Use `word-counter` for basic counts and `text-summarizer` for the main points.
