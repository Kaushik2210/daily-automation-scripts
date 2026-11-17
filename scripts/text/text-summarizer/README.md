# text-summarizer

## Purpose
Get the gist of a long article, report or email without reading all of it. The tool scores every sentence by how many of the text's most frequent meaningful words it contains (ignoring common words like "the" and "and"), gives a small bonus to the first sentence of each paragraph, and prints the best few in their original order. It works fully offline and needs no AI service.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python text_summarizer.py FILE.txt [-n 3] [--bullets]
```
`-n` is how many sentences to keep (default 3). `--bullets` prints one bullet per sentence instead of a paragraph. A line at the end shows how much of the text was kept. The exit code is 1 when the text is too short to summarise.

## Example
```bash
python text_summarizer.py article-long.txt -n 3 --bullets
```
```
- Solar power is growing faster than any other source of electricity.
- Solar panels produce no electricity at night and very little during storms.
- In the coming years, experts expect solar power to supply a quarter of the world's electricity.

Kept 3 of 18 sentence(s): 39 of 245 words (15%).
```

## Notes
- This is *extractive*: it quotes existing sentences rather than rewriting them, so the result is accurate but can read a little choppy.
- Sentences are split at `. ! ?` followed by a capital letter; common abbreviations like "Dr." and "e.g." don't count as sentence ends.
- Use `keyword-extractor` to list the main topics instead.
